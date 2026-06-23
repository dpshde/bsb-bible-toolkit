// Command bsb-tts-tui is a bubbletea + lipgloss TUI for scripts/mlx_tts.py.
//
// It shells out to the Python mlx_tts.py generate pipeline and renders a
// live, easily legible progress dashboard: per-voice progress bars, spinner,
// current segment preview, and rolling ETA. Press q/esc/ctrl+c to quit;
// the Python subprocess receives SIGINT so checkpoints are preserved.
package main

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"os/exec"
	"os/signal"
	"regexp"
	"strconv"
	"strings"
	"syscall"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/bubbles/progress"
	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/lipgloss"
)

const (
	defaultPythonBin = "python3"
	defaultScript    = "scripts/mlx_tts.py"
	padding          = 2
)

var (
	// [af_heart] +1/17 The Lord is my shepherd;... audio=1.2s seg=3.4s avg=3.4s elapsed=3s ETA=54s (16 left)
	progressRe = regexp.MustCompile(
		`^\[(?P<voice>[^\]]+)\] \+(?P<done>\d+)/(?P<total>\d+) (?P<text>.*?)\.\.\. ` +
			`audio=(?P<audio>[\d.]+)s ` +
			`seg=(?P<seg>[\d.]+)s ` +
			`avg=(?P<avg>[\d.]+)s ` +
			`elapsed=(?P<elapsed>\S+) ` +
			`ETA=(?P<eta>\S+) ` +
			`\((?P<left>\d+) left\)`,
	)
	// [af_heart] done: 17 segments, audio=51.0s, rendered in 48s
	doneRe = regexp.MustCompile(
		`^\[(?P<voice>[^\]]+)\] done: (?P<total>\d+) segments, ` +
			`audio=(?P<audio>[\d.]+)s, ` +
			`rendered in (?P<elapsed>\S+)`,
	)
	// [af_heart] 3/17 segments already complete
	skipRe = regexp.MustCompile(`^\[(?P<voice>[^\]]+)\] (?P<done>\d+)/(?P<total>\d+) segments already complete`)

	// [af_heart] SKIP 8/17 text... (error)
	skipSegRe = regexp.MustCompile(
		`^\[(?P<voice>[^\]]+)\] SKIP (?P<done>\d+)/(?P<total>\d+) (?P<text>.*?)\.\.\. \((?P<err>.+)\)`,
	)

	// Built N segments for psalm-23
	builtRe = regexp.MustCompile(`^Built (?P<total>\d+) segments for (?P<dir>\S+)`)

	// BATCH: N chapter(s) x M voice(s)
	batchInitRe = regexp.MustCompile(`^BATCH: (?P<chapters>\d+) chapter\(s\) x (?P<voices>\d+) voice\(s\)`)

	// BATCH +1/9 Psalm 23 [af_heart] 46.7s audio elapsed=4s ETA=31s
	batchProgressRe = regexp.MustCompile(
		`^BATCH \+(?P<done>\d+)/(?P<total>\d+) ` +
			`(?P<book>\S+) (?P<chapter>\S+) ` +
			`\[(?P<voice>[^\]]+)\] ` +
			`(?P<audio>[\d.]+)s audio ` +
			`elapsed=(?P<elapsed>\S+) ` +
			`ETA=(?P<eta>\S+)`,
	)

	// BATCH done: N render(s), M segments, Xm
	batchDoneRe = regexp.MustCompile(`^BATCH done: (?P<renders>\d+) render\(s\), (?P<segments>\d+) segments, (?P<elapsed>\S+)`)
)

type voiceState struct {
	name       string
	done       int
	total      int
	text       string
	audioDur   float64
	segSec     float64
	avgSec     float64
	elapsedStr string
	etaStr     string
	left       int
	phase      string // "idle", "rendering", "done", "error"
}

type model struct {
	pythonBin string
	args      []string
	script    string
	voices    []string
	header    string

	width  int
	height int

	spinner   spinner.Model
	progress  progress.Model
	voiceMap  map[string]*voiceState
	voiceOrder []string

	phase      string // "starting", "rendering", "done", "error"
	errMsg     string
	cmd        *exec.Cmd
	startTime  time.Time

	// Batch state
	batchTotal    int
	batchDone     int
	batchCurrent  string

	quitting bool
	dryRun   bool
}

type progressMsg struct {
	voice    string
	done     int
	total    int
	text     string
	audio    float64
	seg      float64
	avg      float64
	elapsed  string
	eta      string
	left     int
}

type voiceDoneMsg struct {
	voice   string
	total   int
	audio   float64
	elapsed string
}

type builtMsg struct {
	total int
	dir   string
}

type skipMsg struct {
	voice string
	done  int
	total int
}

type errMsg struct{ err error }

func (e errMsg) Error() string { return e.err.Error() }

type quitMsg struct{}

type processExitMsg struct{ err error }

type tickMsg struct{}

// skipSegMsg is sent when mlx-audio crashes on a segment and it gets skipped.
type skipSegMsg struct {
	voice string
	done  int
	total int
	text  string
	err   string
}

// batchInitMsg carries the total number of chapter-voice renders.
type batchInitMsg struct {
	total int
}

// batchProgressMsg is sent after each chapter-voice render completes.
type batchProgressMsg struct {
	done     int
	total    int
	book     string
	chapter  string
	voice    string
	audio    float64
	elapsed  string
	eta      string
}

// batchDoneMsg is sent when the entire batch finishes.
type batchDoneMsg struct {
	renders   int
	segments  int
	elapsed   string
}

// startedMsg carries the exec.Cmd back to the model so Update can store it.
type startedMsg struct {
	cmd    *exec.Cmd
	errMsg string
}

func initialModel(pythonBin, script string, voices []string, args []string) model {
	s := spinner.New()
	s.Spinner = spinner.Dot

	p := progress.New(
		progress.WithDefaultGradient(),
		progress.WithoutPercentage(),
	)

	m := model{
		pythonBin:  pythonBin,
		script:     script,
		args:       args,
		voices:     voices,
		voiceOrder: voices,
		spinner:    s,
		progress:   p,
		voiceMap:   make(map[string]*voiceState),
		phase:      "starting",
		header:     fmt.Sprintf("BSB MLX TTS  %s", strings.Join(voices, ", ")),
		startTime:  time.Now(),
	}
	for _, v := range voices {
		m.voiceMap[v] = &voiceState{name: v, phase: "idle"}
	}
	return m
}

func (m model) Init() tea.Cmd {
	return tea.Batch(m.spinner.Tick, startRender(&m), tickProcess())
}

// tickProcess polls for process exit as a fallback to globalProgram.Send.
func tickProcess() tea.Cmd {
	return tea.Tick(500*time.Millisecond, func(t time.Time) tea.Msg {
		return tickMsg{}
	})
}

func startRender(m *model) tea.Cmd {
	return func() tea.Msg {
		if m.dryRun {
			go m.runFakeProgress()
			return startedMsg{cmd: nil}
		}
		args := append([]string{m.script}, m.args...)
		cmd := exec.Command(m.pythonBin, args...)
		cmd.Env = append(os.Environ(), "PYTHONUNBUFFERED=1")

		stderr, err := cmd.StderrPipe()
		if err != nil {
			return startedMsg{cmd: nil, errMsg: err.Error()}
		}
		stdout, err := cmd.StdoutPipe()
		if err != nil {
			return startedMsg{cmd: nil, errMsg: err.Error()}
		}

		if err := cmd.Start(); err != nil {
			return startedMsg{cmd: nil, errMsg: err.Error()}
		}

		// Goroutine to read stderr (where mlx_tts.py prints progress) and send messages.
		go pumpStderr(stderr)

		// Drain stdout to /dev/null (Python prints manifest path there).
		go func() {
			_, _ = io.Copy(io.Discard, stdout)
		}()

		// Wait for process completion in background.
		go func() {
			err := cmd.Wait()
			if err != nil {
				if exitErr, ok := err.(*exec.ExitError); ok {
					if status, ok := exitErr.Sys().(syscall.WaitStatus); ok && status.Signaled() {
						if sig := status.Signal(); sig == syscall.SIGINT || sig == syscall.SIGTERM {
							return
						}
					}
				}
			}
			// Brief delay to let stderr reader finish flushing.
			time.Sleep(200 * time.Millisecond)
			globalProgram.Send(processExitMsg{err: err})
		}()

		return startedMsg{cmd: cmd}
	}
}

// stderrLines collects non-progress stderr output for error reporting.
var stderrLines []string

// ansiRe matches ANSI escape sequences (color codes, cursor moves, etc).
var ansiRe = regexp.MustCompile(`\x1b\[[0-9;]*[a-zA-Z]`)

func pumpStderr(pipe io.ReadCloser) {
	scanner := bufio.NewScanner(pipe)
	scanner.Buffer(make([]byte, 0, 1024*1024), 1024*1024)
	for scanner.Scan() {
		line := scanner.Text()
		// Strip ANSI escape sequences.
		line = ansiRe.ReplaceAllString(line, "")
		// Strip carriage returns and content before the last \r to handle
		// tqdm progress bars that use \r without \n.
		if idx := strings.LastIndex(line, "\r"); idx >= 0 {
			line = line[idx+1:]
		}
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		msg := parseLine(line)
		if msg != nil {
			sendMsg(msg)
		} else {
			// Keep last 10 unmatched lines for error diagnostics.
			stderrLines = append(stderrLines, line)
			if len(stderrLines) > 10 {
				stderrLines = stderrLines[len(stderrLines)-10:]
			}
		}
	}
}

// globalProgram holds the *tea.Program so background goroutines can Send.
var globalProgram *tea.Program

func sendMsg(msg tea.Msg) {
	if globalProgram != nil {
		globalProgram.Send(msg)
	}
}

// runFakeProgress emits simulated progress messages for non-interactive testing.
func (m *model) runFakeProgress() {
	total := 17
	time.Sleep(500 * time.Millisecond)
	globalProgram.Send(builtMsg{total: total, dir: "psalm-23"})
	verseTexts := []string{
		"Psalm 23.", "The Lord is my shepherd;", "I shall not want.",
		"He makes me lie down in green pastures;", "He leads me beside quiet waters.",
		"He restores my soul;", "He guides me in paths of righteousness;",
		"Even though I walk through the valley", "I will fear no evil, for You are with me;",
		"Your rod and Your staff, they comfort me.", "You prepare a table before me;",
		"You anoint my head with oil;", "my cup overflows.",
		"Surely goodness and mercy will follow me", "all the days of my life,",
		"and I will dwell in the house of the Lord", "forever.",
	}
	for _, voice := range m.voiceOrder {
		for i := 1; i <= total; i++ {
			time.Sleep(800 * time.Millisecond)
			left := total - i
			seg := 3.0 + float64(i%3)*0.5
			audio := float64(i) * 3.0
			elapsed := time.Duration(i) * time.Duration(seg*float64(time.Second))
			eta := time.Duration(left) * time.Duration(seg*float64(time.Second))
			text := verseTexts[i-1]
			globalProgram.Send(progressMsg{
				voice:   voice,
				done:    i,
				total:   total,
				text:    text,
				audio:   audio,
				seg:     seg,
				avg:     seg,
				elapsed: formatDur(elapsed),
				eta:     formatDur(eta),
				left:    left,
			})
		}
		globalProgram.Send(voiceDoneMsg{
			voice:   voice,
			total:   total,
			audio:   float64(total) * 3.0,
			elapsed: formatDur(time.Duration(total*3) * time.Second),
		})
	}
}

func formatDur(d time.Duration) string {
	d = d.Round(time.Second)
	if d < time.Minute {
		return fmt.Sprintf("%ds", int(d.Seconds()))
	}
	m := int(d.Minutes())
	s := int(d.Seconds()) % 60
	return fmt.Sprintf("%dm%02ds", m, s)
}

func parseLine(line string) tea.Msg {
	if matches := progressRe.FindStringSubmatch(line); matches != nil {
		done, _ := strconv.Atoi(matches[2])
		total, _ := strconv.Atoi(matches[3])
		audio, _ := strconv.ParseFloat(matches[5], 64)
		seg, _ := strconv.ParseFloat(matches[6], 64)
		avg, _ := strconv.ParseFloat(matches[7], 64)
		left, _ := strconv.Atoi(matches[10])
		return progressMsg{
			voice:   matches[1],
			done:    done,
			total:   total,
			text:    matches[4],
			audio:   audio,
			seg:     seg,
			avg:     avg,
			elapsed: matches[8],
			eta:     matches[9],
			left:    left,
		}
	}
	if matches := doneRe.FindStringSubmatch(line); matches != nil {
		total, _ := strconv.Atoi(matches[2])
		audio, _ := strconv.ParseFloat(matches[3], 64)
		return voiceDoneMsg{
			voice:   matches[1],
			total:   total,
			audio:   audio,
			elapsed: matches[4],
		}
	}
	if matches := skipRe.FindStringSubmatch(line); matches != nil {
		done, _ := strconv.Atoi(matches[2])
		total, _ := strconv.Atoi(matches[3])
		return skipMsg{voice: matches[1], done: done, total: total}
	}
	if matches := skipSegRe.FindStringSubmatch(line); matches != nil {
		done, _ := strconv.Atoi(matches[2])
		total, _ := strconv.Atoi(matches[3])
		return skipSegMsg{
			voice: matches[1],
			done:  done,
			total: total,
			text:  matches[4],
			err:   matches[5],
		}
	}
	if matches := builtRe.FindStringSubmatch(line); matches != nil {
		total, _ := strconv.Atoi(matches[1])
		return builtMsg{total: total, dir: matches[2]}
	}
	if matches := batchInitRe.FindStringSubmatch(line); matches != nil {
		// chapters * voices
		chapters, _ := strconv.Atoi(matches[1])
		voices, _ := strconv.Atoi(matches[2])
		return batchInitMsg{total: chapters * voices}
	}
	if matches := batchProgressRe.FindStringSubmatch(line); matches != nil {
		done, _ := strconv.Atoi(matches[1])
		total, _ := strconv.Atoi(matches[2])
		audio, _ := strconv.ParseFloat(matches[6], 64)
		return batchProgressMsg{
			done:    done,
			total:   total,
			book:    matches[3],
			chapter: matches[4],
			voice:   matches[5],
			audio:   audio,
			elapsed: matches[7],
			eta:     matches[8],
		}
	}
	if matches := batchDoneRe.FindStringSubmatch(line); matches != nil {
		renders, _ := strconv.Atoi(matches[1])
		segments, _ := strconv.Atoi(matches[2])
		return batchDoneMsg{
			renders:  renders,
			segments: segments,
			elapsed:  matches[3],
		}
	}
	return nil
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
	case startedMsg:
		if msg.errMsg != "" {
			m.phase = "error"
			m.errMsg = msg.errMsg
			return m, tea.Tick(5*time.Second, func(t time.Time) tea.Msg { return quitMsg{} })
		}
		m.cmd = msg.cmd
		m.startTime = time.Now()
	case quitMsg:
		m.quitting = true
		return m, tea.Quit
	case tickMsg:
		if m.phase == "starting" && m.cmd != nil {
			if m.cmd.ProcessState != nil && m.cmd.ProcessState.Exited() {
				m.phase = "error"
				if len(stderrLines) > 0 {
					m.errMsg = strings.Join(stderrLines, "\n")
				} else {
					m.errMsg = "Python process exited before producing any output"
				}
				return m, tea.Tick(5*time.Second, func(t time.Time) tea.Msg { return quitMsg{} })
			}
		}
		if !m.quitting && m.phase != "done" && m.phase != "error" {
			return m, tickProcess()
		}
	case tea.KeyMsg:
		switch msg.String() {
		case "q", "esc":
			m.quitting = true
			return m, tea.Quit
		case "ctrl+c":
			m.quitting = true
			return m, tea.Quit
		}
	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd
	case progress.FrameMsg:
		model, cmd := m.progress.Update(msg)
		m.progress = model.(progress.Model)
		return m, cmd
	case builtMsg:
		m.phase = "rendering"
		for _, v := range m.voiceMap {
			v.total = msg.total
		}
	case batchInitMsg:
		m.batchTotal = msg.total
		m.phase = "rendering"
	case batchProgressMsg:
		m.phase = "rendering"
		m.batchDone = msg.done
		m.batchTotal = msg.total
		m.batchCurrent = fmt.Sprintf("%s %s [%s]", msg.book, msg.chapter, msg.voice)
	case batchDoneMsg:
		m.phase = "done"
		m.batchDone = m.batchTotal
		return m, tea.Quit
	case skipMsg:
		vs := m.voiceMap[msg.voice]
		if vs != nil {
			vs.done = msg.done
			vs.total = msg.total
			if msg.done >= msg.total {
				vs.phase = "done"
			}
		}
	case skipSegMsg:
		vs := m.voiceMap[msg.voice]
		if vs == nil {
			vs = &voiceState{name: msg.voice}
			m.voiceMap[msg.voice] = vs
			m.voiceOrder = append(m.voiceOrder, msg.voice)
		}
		vs.done = msg.done
		vs.total = msg.total
		vs.text = fmt.Sprintf("SKIP: %s", msg.err)
		vs.phase = "rendering"
	case progressMsg:
		m.phase = "rendering"
		vs := m.voiceMap[msg.voice]
		if vs == nil {
			vs = &voiceState{name: msg.voice}
			m.voiceMap[msg.voice] = vs
			m.voiceOrder = append(m.voiceOrder, msg.voice)
		}
		vs.done = msg.done
		vs.total = msg.total
		vs.text = msg.text
		vs.audioDur = msg.audio
		vs.segSec = msg.seg
		vs.avgSec = msg.avg
		vs.elapsedStr = msg.elapsed
		vs.etaStr = msg.eta
		vs.left = msg.left
		vs.phase = "rendering"
	case voiceDoneMsg:
		vs := m.voiceMap[msg.voice]
		if vs != nil {
			vs.done = msg.total
			vs.total = msg.total
			vs.phase = "done"
			vs.etaStr = ""
			vs.audioDur = msg.audio
			vs.elapsedStr = msg.elapsed
			vs.left = 0
		}
		allDone := true
		for _, v := range m.voiceMap {
			if v.phase != "done" {
				allDone = false
				break
			}
		}
		if allDone {
			m.phase = "done"
			return m, tea.Quit
		}
	case errMsg:
		m.phase = "error"
		m.errMsg = msg.Error()
		return m, tea.Quit
	case processExitMsg:
		// Process exited. If we were still "starting", it failed before any progress.
		if m.phase == "starting" {
			m.phase = "error"
			if len(stderrLines) > 0 {
				m.errMsg = strings.Join(stderrLines, "\n")
			} else if msg.err != nil {
				m.errMsg = msg.err.Error()
			} else {
				m.errMsg = "Python process exited before producing any output"
			}
			return m, tea.Tick(5*time.Second, func(t time.Time) tea.Msg { return quitMsg{} })
		}
		// If rendering, check if all voices completed.
		allDone := true
		for _, v := range m.voiceMap {
			if v.phase != "done" {
				allDone = false
				break
			}
		}
		if allDone {
			m.phase = "done"
		} else if len(stderrLines) > 0 {
			m.phase = "error"
			m.errMsg = strings.Join(stderrLines, "\n")
		}
	}
	return m, nil
}

func (m model) View() string {
	if m.width == 0 {
		m.width = 80
	}

	var b strings.Builder

	// Header
	headerStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("63")).
		Padding(0, 1)
	subStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("245")).
		Italic(true)

	title := headerStyle.Render("BSB MLX TTS")
	subtitle := subStyle.Render(fmt.Sprintf("  %s  (%s)", strings.Join(m.voiceOrder, ", "), time.Since(m.startTime).Truncate(time.Second)))

	borderStyle := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("63")).
		Padding(1, 2).
		Width(m.width - 4)

	b.WriteString(lipgloss.JoinHorizontal(lipgloss.Center, title, subtitle))
	b.WriteString("\n\n")

	// Batch progress bar
	if m.batchTotal > 0 {
		b.WriteString(renderBatchPanel(&m))
		b.WriteString("\n\n")
	}

	// Per-voice panels
	for i, name := range m.voiceOrder {
		vs := m.voiceMap[name]
		if vs == nil {
			continue
		}
		if i > 0 {
			b.WriteString("\n")
		}
		b.WriteString(renderVoicePanel(vs, m.width-4))
	}

	// Status / footer
	b.WriteString("\n")
	status := m.renderStatus()
	b.WriteString(status)

	content := b.String()
	return borderStyle.Render(content)
}

func renderBatchPanel(m *model) string {
	nameStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("39"))
	dimStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("245"))

	pct := 0.0
	if m.batchTotal > 0 {
		pct = float64(m.batchDone) / float64(m.batchTotal)
	}

	barWidth := m.width - 30
	if barWidth < 10 {
		barWidth = 10
	}
	bar := renderBar(pct, barWidth)

	lines := []string{
		fmt.Sprintf("%s  %d/%d chapters", nameStyle.Render("BATCH"), m.batchDone, m.batchTotal),
		bar,
	}
	if m.batchCurrent != "" && m.batchDone < m.batchTotal {
		lines = append(lines, dimStyle.Render(fmt.Sprintf("Now: %s", m.batchCurrent)))
	}

	panelStyle := lipgloss.NewStyle().
		BorderLeft(true).
		BorderForeground(lipgloss.Color("39")).
		Padding(0, 0, 0, 1).
		Width(m.width - 4)

	return panelStyle.Render(strings.Join(lines, "\n"))
}

func renderVoicePanel(vs *voiceState, width int) string {
	nameStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("39"))

	phaseStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("245"))

	doneStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("46"))

	dimStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("245"))

	var phaseTag string
	switch vs.phase {
	case "idle":
		phaseTag = phaseStyle.Render("waiting...")
	case "rendering":
		phaseTag = fmt.Sprintf("%s %s", vs.text, phaseStyle.Render("rendering"))
	case "done":
		phaseTag = doneStyle.Render("done")
	case "error":
		phaseTag = lipgloss.NewStyle().Foreground(lipgloss.Color("196")).Render("error")
	}

	header := fmt.Sprintf("%s  %d/%d", nameStyle.Render(vs.name), vs.done, vs.total)
	if vs.total > 0 {
		pct := float64(vs.done) / float64(vs.total)
		header += "  " + dimStyle.Render(fmt.Sprintf("(%.0f%%)", pct*100))
	}

	// Progress bar
	barWidth := width - 20
	if barWidth < 10 {
		barWidth = 10
	}
	pct := 0.0
	if vs.total > 0 {
		pct = float64(vs.done) / float64(vs.total)
	}
	bar := renderBar(pct, barWidth)

	var lines []string
	lines = append(lines, header)
	lines = append(lines, bar)
	lines = append(lines, phaseTag)

	if vs.phase == "rendering" && vs.total > 0 && vs.done > 0 {
		stats := fmt.Sprintf(
			"seg %s  avg %s  audio %s  elapsed %s  ETA %s  (%d left)",
			fmt.Sprintf("%.1fs", vs.segSec),
			fmt.Sprintf("%.1fs", vs.avgSec),
			fmt.Sprintf("%.1fs", vs.audioDur),
			vs.elapsedStr,
			colorizeETA(vs.etaStr, vs.avgSec, vs.left),
			vs.left,
		)
		lines = append(lines, dimStyle.Render(stats))
	}
	if vs.phase == "done" {
		summary := fmt.Sprintf(
			"rendered in %s  (audio %.1fs)",
			vs.elapsedStr,
			vs.audioDur,
		)
		lines = append(lines, doneStyle.Render(summary))
	}

	panelStyle := lipgloss.NewStyle().
		BorderLeft(true).
		BorderForeground(lipgloss.Color("63")).
		Padding(0, 0, 0, 1).
		Width(width)

	return panelStyle.Render(strings.Join(lines, "\n"))
}

func renderBar(pct float64, width int) string {
	filled := int(pct * float64(width))
	if filled > width {
		filled = width
	}
	if filled < 0 {
		filled = 0
	}
	filledStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("39"))
	emptyStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("238"))
	return filledStyle.Render(strings.Repeat("█", filled)) + emptyStyle.Render(strings.Repeat("░", width-filled))
}

func colorizeETA(eta string, avgSec float64, left int) string {
	if left == 0 {
		return lipgloss.NewStyle().Foreground(lipgloss.Color("46")).Render(eta)
	}
	// Roughly: each segment averages avgSec. Total remaining ETA = avgSec*left.
	// Color by magnitude: green <30s, yellow <120s, red otherwise.
	totalSec := avgSec * float64(left)
	style := lipgloss.NewStyle()
	switch {
	case totalSec < 30:
		style = style.Foreground(lipgloss.Color("46"))
	case totalSec < 120:
		style = style.Foreground(lipgloss.Color("220"))
	default:
		style = style.Foreground(lipgloss.Color("208"))
	}
	return style.Render(eta)
}

func (m model) renderStatus() string {
	footerStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("245"))

	switch m.phase {
	case "starting":
		return footerStyle.Render(fmt.Sprintf("%s  starting up...", m.spinner.View()))
	case "rendering":
		return footerStyle.Render(fmt.Sprintf("%s  rendering  |  q to quit (checkpoints preserved)", m.spinner.View()))
	case "done":
		return lipgloss.NewStyle().Foreground(lipgloss.Color("46")).Render("all voices complete")
	case "error":
		errStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("196")).Bold(true)
		detailStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("245"))
		msg := errStyle.Render("Error: Python process exited unexpectedly")
		if m.errMsg != "" {
			// Truncate long errors but show the key part.
			errText := m.errMsg
			if len(errText) > 300 {
				errText = errText[:300] + "..."
			}
			msg += "\n" + detailStyle.Render(errText)
		}
		return msg
	}
	return ""
}

// buildPythonArgs builds the args for either generate or batch subcommand.
func buildPythonArgs(batchRange, books string, all, sequence bool, book, chapter string, voices []string, model, quantize string, fresh bool) []string {
	var result []string

	if sequence {
		result = append(result, "batch", "--sequence")
	} else if all || books != "" || batchRange != "" {
		result = append(result, "batch")
		if all {
			result = append(result, "--all")
		}
		if books != "" {
			result = append(result, "--books", books)
		}
		if batchRange != "" {
			result = append(result, "--range", batchRange)
		}
	} else {
		result = append(result, "generate", "--book", book, "--chapter", chapter)
	}

	for _, v := range voices {
		result = append(result, "--voice", v)
	}
	if model != "" {
		result = append(result, "--model", model)
	}
	if quantize != "" {
		result = append(result, "--quantize", quantize)
	}
	if fresh {
		result = append(result, "--fresh")
	}
	return result
}

func main() {
	book := flagStr("book", "Psalm")
	chapter := flagStr("chapter", "23")
	model := flagStr("model", "")
	quantize := flagStr("quantize", "")
	voicesFlag := flagString("voices", "af_heart,bm_george")
	pythonBin := flagString("python", defaultPythonBin)
	script := flagString("script", defaultScript)
	fresh := flagBool("fresh", false)
	_ = flagBool("play", false) // reserved for future use
	dryRun := flagBool("dry-run", false)
	batchRange := flagString("range", "")
	books := flagString("books", "")
	all := flagBool("all", false)
	sequence := flagBool("sequence", false)

	voices := strings.Split(voicesFlag, ",")

	pythonArgs := buildPythonArgs(batchRange, books, all, sequence, book, chapter, voices, model, quantize, fresh)

	m := initialModel(pythonBin, script, voices, pythonArgs)
	m.dryRun = dryRun

	// Set up SIGINT handler so Ctrl+C at the terminal sends SIGINT to the Python child too.
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-sigCh
		if m.cmd != nil && m.cmd.Process != nil {
			_ = m.cmd.Process.Signal(syscall.SIGINT)
		}
		os.Exit(130)
	}()

	p := tea.NewProgram(m, tea.WithAltScreen())
	globalProgram = p
	if _, err := p.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		os.Exit(1)
	}

	// On clean exit, if Python is still running (shouldn't be), clean up.
	if m.cmd != nil && m.cmd.Process != nil {
		_ = m.cmd.Process.Signal(syscall.SIGTERM)
	}
}

// Lightweight flag parsing helpers (avoids importing "flag" which conflicts with bubbles/progress.FrameMsg).

func flagString(name, defaultVal string) string {
	for i, arg := range os.Args[1:] {
		if arg == "--"+name && i+1 < len(os.Args[1:]) {
			return os.Args[i+2]
		}
		if strings.HasPrefix(arg, "--"+name+"=") {
			return strings.TrimPrefix(arg, "--"+name+"=")
		}
	}
	return defaultVal
}

func flagStr(name, defaultVal string) string {
	return flagString(name, defaultVal)
}

func flagBool(name string, defaultVal bool) bool {
	for _, arg := range os.Args[1:] {
		if arg == "--"+name {
			return true
		}
		if strings.HasPrefix(arg, "--"+name+"=") {
			val := strings.TrimPrefix(arg, "--"+name+"=")
			return val == "true" || val == "1"
		}
	}
	return defaultVal
}
