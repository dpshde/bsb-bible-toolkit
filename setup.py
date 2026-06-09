from setuptools import find_packages, setup


setup(
    name="bsb-bible-pdf-toolkit",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages("src"),
    entry_points={
        "console_scripts": [
            "bsb-design=bsb_pdf_toolkit.design:main",
            "bsb-add-route-links=bsb_pdf_toolkit.add_route_links:main",
            "bsb-change-font=bsb_pdf_toolkit.change_font:main",
            "bsb-customize-pdf=bsb_pdf_toolkit.customize_bsb:main",
            "bsb-customize-epub=bsb_pdf_toolkit.customize_epub:main",
            "bsb-download=bsb_pdf_toolkit.download_bsb:main",
            "bsb-extract=bsb_pdf_toolkit.extract_bsb:main",
            "bsb-reflow-pdf=bsb_pdf_toolkit.generate_reflow_pdf:main",
            "bsb-typst-pdf=bsb_pdf_toolkit.generate_typst_pdf:main",
            "bsb-compare-renders=bsb_pdf_toolkit.compare_renders:main",
            "bsb-verify-artifacts=bsb_pdf_toolkit.verify_artifacts:main",
        ],
    },
)
