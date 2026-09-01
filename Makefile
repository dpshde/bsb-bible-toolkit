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
MILO_DIR := fonts/milo
GRID_DIR := fonts/grid-proof

.PHONY: help usfm-source travel-john travel-john-typst travel-john-grid-proof test-travel test-travel-unit

help:
	@echo "usfm-source              Download official BSB USFM if missing"
	@echo "travel-john-typst        Compose John Typst (no fonts required)"
	@echo "travel-john              Compile the travel John PDF (requires Milo)"
	@echo "travel-john-grid-proof   Watermarked OFL metrics PDF (not the loved face)"
	@echo "test-travel              Unit tests for the travel composer"

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

test-travel test-travel-unit:
	$(PYTHON) -m pytest tests/test_travel_pdf.py -q
