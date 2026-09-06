# BSB Bible Toolkit — local build entry points.
# The travel print target requires licensed FF Milo Serif in fonts/milo/.

PYTHON ?= python3
export PYTHONPATH := src

USFM := drafts/primary/source/engbsb_usfm.zip
USFM_URL := https://bereanbible.com/bsb_usfm.zip
TRAVEL_PDF := drafts/travel/bsb-travel-john.pdf
TRAVEL_TYP := drafts/travel/work/john.typ
TRAVEL_GRID_PDF := drafts/travel/bsb-travel-john-grid-proof.pdf
TRAVEL_GRID_TYP := drafts/travel/work/john-grid-proof.typ
TRAVEL_BIBLE_GRID_PDF := drafts/travel/bsb-travel-bible-grid-proof.pdf
TRAVEL_BIBLE_GRID_TYP := drafts/travel/work/bible-grid-proof.typ
TRAVEL_BIBLE_OT_GRID_PDF := drafts/travel/bsb-travel-bible-ot-grid-proof.pdf
TRAVEL_BIBLE_OT_GRID_TYP := drafts/travel/work/bible-ot-grid-proof.typ
TRAVEL_BIBLE_NT_GRID_PDF := drafts/travel/bsb-travel-bible-nt-grid-proof.pdf
TRAVEL_BIBLE_NT_GRID_TYP := drafts/travel/work/bible-nt-grid-proof.typ
TRAVEL_SPREADS_PDF := drafts/travel/bsb-travel-john-spreads-grid-proof.pdf
TRAVEL_SPREADS_DIR := drafts/travel/spreads
TRAVEL_HOTSPOT_PDF := drafts/travel/bsb-travel-hotspot-sampler-grid-proof.pdf
TRAVEL_HOTSPOT_DIR := drafts/travel/hotspots
MILO_DIR := fonts/milo
GRID_DIR := fonts/grid-proof

.PHONY: help usfm-source travel-john travel-john-typst travel-john-grid-proof \
	travel-john-spreads travel-hotspot-sampler travel-bible-grid-proof \
	travel-bible-ot-grid-proof travel-bible-nt-grid-proof test-travel \
	test-travel-unit

help:
	@echo "usfm-source                 Download official BSB USFM if missing"
	@echo "travel-john-typst           Compose John Typst (no fonts required)"
	@echo "travel-john                 Compile the travel John PDF (requires Milo)"
	@echo "travel-john-grid-proof      Watermarked John OFL metrics PDF (not the loved face)"
	@echo "travel-john-spreads         2-up John openings 2–3, 4–5, 10–11 (grid proof)"
	@echo "travel-hotspot-sampler      Compact committed hotspot leaves (grid proof)"
	@echo "travel-bible-grid-proof     Watermarked 66-book OFL metrics PDF (not the loved face)"
	@echo "travel-bible-ot-grid-proof  OT-only fallback of the grid-proof compile"
	@echo "travel-bible-nt-grid-proof  NT-only fallback of the grid-proof compile"
	@echo "test-travel                 Unit tests for the travel composer"

usfm-source:
	@mkdir -p drafts/primary/source
	@if [ ! -f "$(USFM)" ]; then \
		echo "Downloading official BSB USFM from $(USFM_URL)"; \
		curl -fsSL -o "$(USFM)" "$(USFM_URL)"; \
	fi

travel-john-typst: usfm-source
	$(PYTHON) -m bsb_pdf_toolkit.generate_travel_pdf \
		$(USFM) $(TRAVEL_PDF) \
		--typst-out $(TRAVEL_TYP) \
		--font-dir $(MILO_DIR) \
		--no-compile

travel-john: usfm-source
	$(PYTHON) -m bsb_pdf_toolkit.generate_travel_pdf \
		$(USFM) $(TRAVEL_PDF) \
		--typst-out $(TRAVEL_TYP) \
		--font-dir $(MILO_DIR)

travel-john-grid-proof: usfm-source
	$(PYTHON) -m bsb_pdf_toolkit.generate_travel_pdf \
		$(USFM) $(TRAVEL_GRID_PDF) \
		--typst-out $(TRAVEL_GRID_TYP) \
		--font-dir $(GRID_DIR) \
		--grid-proof

travel-john-spreads: travel-john-grid-proof
	$(PYTHON) -m bsb_pdf_toolkit.compose_travel_spreads \
		$(TRAVEL_GRID_PDF) $(TRAVEL_SPREADS_PDF) \
		--png-dir $(TRAVEL_SPREADS_DIR)

travel-hotspot-sampler: usfm-source
	$(PYTHON) -m bsb_pdf_toolkit.compose_travel_hotspots \
		--usfm $(USFM) \
		--output $(TRAVEL_HOTSPOT_PDF) \
		--png-dir $(TRAVEL_HOTSPOT_DIR)

travel-bible-grid-proof: usfm-source
	$(PYTHON) -m bsb_pdf_toolkit.generate_travel_pdf \
		$(USFM) $(TRAVEL_BIBLE_GRID_PDF) \
		--typst-out $(TRAVEL_BIBLE_GRID_TYP) \
		--font-dir $(GRID_DIR) \
		--grid-proof \
		--all-books

travel-bible-ot-grid-proof: usfm-source
	$(PYTHON) -m bsb_pdf_toolkit.generate_travel_pdf \
		$(USFM) $(TRAVEL_BIBLE_OT_GRID_PDF) \
		--typst-out $(TRAVEL_BIBLE_OT_GRID_TYP) \
		--font-dir $(GRID_DIR) \
		--grid-proof \
		--all-books \
		--testament ot

travel-bible-nt-grid-proof: usfm-source
	$(PYTHON) -m bsb_pdf_toolkit.generate_travel_pdf \
		$(USFM) $(TRAVEL_BIBLE_NT_GRID_PDF) \
		--typst-out $(TRAVEL_BIBLE_NT_GRID_TYP) \
		--font-dir $(GRID_DIR) \
		--grid-proof \
		--all-books \
		--testament nt

test-travel test-travel-unit:
	$(PYTHON) -m pytest tests/test_travel_pdf.py -q
