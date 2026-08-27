#!/usr/bin/env python3
"""Integrate the validated manuscript into the legacy viXra DOCX shell."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import re
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import uno
from PIL import Image
from com.sun.star.awt.FontSlant import NONE
from com.sun.star.awt.FontWeight import BOLD, NORMAL
from com.sun.star.beans import PropertyValue
from com.sun.star.style.ParagraphAdjust import BLOCK, CENTER, LEFT
from com.sun.star.text.ControlCharacter import PARAGRAPH_BREAK
from com.sun.star.text.TextContentAnchorType import AS_CHARACTER


ROOT = Path(__file__).resolve().parents[2]
IMAGE_RE = re.compile(r"!\[(?P<caption>[^]]+)]\((?P<path>[^)]+)\)")
COMMENT_RE = re.compile(r"<!--.*?-->")
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"


def property_value(name: str, value: object) -> PropertyValue:
    prop = PropertyValue()
    prop.Name = name
    prop.Value = value
    return prop


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_markdown(path: Path) -> tuple[str, list[tuple[str, object]]]:
    blocks: list[tuple[str, object]] = []
    paragraph: list[str] = []
    title = ""

    def flush() -> None:
        if paragraph:
            value = " ".join(paragraph).strip()
            if value:
                blocks.append(("paragraph", value))
            paragraph.clear()

    for source_line in path.read_text(encoding="utf-8").splitlines():
        line = COMMENT_RE.sub("", source_line).strip()
        if not line:
            flush()
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            flush()
            level = len(heading.group(1))
            value = heading.group(2).strip()
            if level == 1 and not title:
                title = value
            else:
                blocks.append((f"heading{level}", value))
            continue
        reference = re.match(r"^(\d+)\.\s+(.+)$", line)
        if reference:
            flush()
            blocks.append(("reference", f"{reference.group(1)}. {reference.group(2)}"))
            continue
        image = IMAGE_RE.search(line)
        if image:
            flush()
            prefix = line[: image.start()].strip()
            suffix = line[image.end() :].strip()
            if prefix:
                blocks.append(("paragraph", prefix))
            blocks.append(
                (
                    "image",
                    {
                        "caption": image.group("caption").strip(),
                        "path": (path.parent / image.group("path")).resolve(),
                    },
                )
            )
            if suffix:
                paragraph.append(suffix)
            continue
        paragraph.append(line)
    flush()
    if not title:
        raise ValueError("Validated manuscript has no level-one title")
    return title, blocks


def normalize_text(value: str) -> str:
    value = value.replace("1 frozen pathways", "1 frozen pathway")
    value = value.replace("retained in Table 4 and", "retained in electronic Table 4 and")
    value = value.replace(" >=", " ≥").replace(" <=", " ≤")
    value = value.replace("|log2FC|>=", "|log2FC|≥")
    return value


def connect(port: int):
    local_context = uno.getComponentContext()
    resolver = local_context.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local_context
    )
    context = resolver.resolve(
        f"uno:socket,host=127.0.0.1,port={port};urp;StarOffice.ComponentContext"
    )
    desktop = context.ServiceManager.createInstanceWithContext(
        "com.sun.star.frame.Desktop", context
    )
    return desktop


class WriterBuilder:
    def __init__(self, document) -> None:
        self.document = document
        self.text = document.Text
        self.cursor = self.text.createTextCursor()

    def clear_body(self) -> None:
        self.cursor.gotoEnd(True)
        self.cursor.String = ""
        if self.document.TextTables.Count or self.document.GraphicObjects.Count:
            raise RuntimeError("Legacy tables or figures remained after clearing the body")
        self.cursor.gotoStart(False)

    def paragraph(
        self,
        value: str,
        style: str = "Body Text Indent1",
        *,
        align=BLOCK,
        font_size: float = 11.0,
        bold: bool = False,
        first_indent: int | None = None,
        before: int = 0,
        after: int = 150,
    ) -> None:
        self.cursor.gotoEnd(False)
        self.cursor.ParaStyleName = style
        self.cursor.ParaAdjust = align
        self.cursor.ParaTopMargin = before
        self.cursor.ParaBottomMargin = after
        if first_indent is not None:
            self.cursor.ParaFirstLineIndent = first_indent
        self.cursor.CharFontName = "Arial"
        self.cursor.CharFontNameAsian = "Arial"
        self.cursor.CharFontNameComplex = "Arial"
        self.cursor.CharHeight = font_size
        self.cursor.CharHeightAsian = font_size
        self.cursor.CharHeightComplex = font_size
        self.cursor.CharWeight = BOLD if bold else NORMAL
        self.cursor.CharWeightAsian = BOLD if bold else NORMAL
        self.cursor.CharWeightComplex = BOLD if bold else NORMAL
        self.cursor.CharPosture = NONE
        self.cursor.CharPostureAsian = NONE
        self.cursor.CharPostureComplex = NONE
        self.text.insertString(self.cursor, normalize_text(value), False)
        self.text.insertControlCharacter(self.cursor, PARAGRAPH_BREAK, False)

    def heading(self, value: str, level: int) -> None:
        if level == 2:
            self.paragraph(
                value.upper(),
                "Heading 1",
                align=LEFT,
                font_size=11.0,
                bold=True,
                first_indent=0,
                before=280,
                after=120,
            )
        else:
            self.paragraph(
                value,
                "Heading 2",
                align=LEFT,
                font_size=10.5,
                bold=True,
                first_indent=0,
                before=180,
                after=80,
            )

    def caption(self, value: str) -> None:
        self.paragraph(
            value,
            "Caption",
            align=LEFT,
            font_size=9.0,
            first_indent=0,
            before=40,
            after=180,
        )

    def image(self, source: Path, caption: str, temporary_dir: Path) -> None:
        if not source.is_file():
            raise FileNotFoundError(source)
        raster_source = source.with_suffix(".tiff") if source.suffix.lower() == ".svg" else source
        if not raster_source.is_file():
            raise FileNotFoundError(raster_source)
        output = temporary_dir / f"{raster_source.stem}.png"
        with Image.open(raster_source) as image:
            image.thumbnail((2400, 3000), Image.Resampling.LANCZOS)
            if image.mode == "RGBA":
                background = Image.new("RGB", image.size, "white")
                background.paste(image, mask=image.getchannel("A"))
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")
            image.save(output, "PNG", optimize=True)
            pixel_width, pixel_height = image.size

        max_width = 16200
        max_height = 21800
        ratio = pixel_height / pixel_width
        width = max_width
        height = int(width * ratio)
        if height > max_height:
            height = max_height
            width = int(height / ratio)

        self.cursor.gotoEnd(False)
        self.cursor.ParaStyleName = "Standard"
        self.cursor.ParaAdjust = CENTER
        self.cursor.ParaFirstLineIndent = 0
        graphic = self.document.createInstance("com.sun.star.text.TextGraphicObject")
        graphic.AnchorType = AS_CHARACTER
        graphic.GraphicURL = uno.systemPathToFileUrl(str(output.resolve()))
        graphic.Width = width
        graphic.Height = height
        graphic.Title = caption
        graphic.Description = caption
        self.text.insertTextContent(self.cursor, graphic, False)
        self.cursor.gotoEnd(False)
        self.text.insertControlCharacter(self.cursor, PARAGRAPH_BREAK, False)
        self.caption(caption)

    def table(self, caption: str, rows: list[list[str]], *, font_size: float = 8.0) -> None:
        if not rows or not rows[0]:
            raise ValueError(f"Empty table: {caption}")
        width = len(rows[0])
        if any(len(row) != width for row in rows):
            raise ValueError(f"Ragged table: {caption}")
        self.caption(caption)
        self.cursor.gotoEnd(False)
        table = self.document.createInstance("com.sun.star.text.TextTable")
        table.initialize(len(rows), width)
        self.text.insertTextContent(self.cursor, table, False)
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                cell = table.getCellByName(f"{chr(65 + column_index)}{row_index + 1}")
                cell.String = str(value)
                cell_cursor = cell.createTextCursor()
                cell_cursor.gotoEnd(True)
                cell_cursor.CharFontName = "Arial"
                cell_cursor.CharHeight = font_size
                cell_cursor.CharWeight = BOLD if row_index == 0 else NORMAL
                cell_cursor.ParaAdjust = LEFT
                if row_index == 0:
                    cell.BackColor = 0xD9EAF7
        for name, value in (
            ("RepeatHeadline", True),
            ("HeaderRowCount", 1),
            ("Split", True),
        ):
            try:
                setattr(table, name, value)
            except Exception:
                pass
        self.cursor.gotoEnd(False)
        self.text.insertControlCharacter(self.cursor, PARAGRAPH_BREAK, False)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def artifact_inventory() -> list[tuple[str, str]]:
    descriptions = {
        "Table1_dataset_roles_eligibility.tsv": "Dataset roles, estimands, eligibility, and locked limitations.",
        "Table2_frozen_discovery.tsv": "All frozen gene and pathway discoveries.",
        "Table3_internal_robustness.tsv": "Gene and pathway internal-robustness outcomes.",
        "Table4_external_evaluation.tsv": "All external frozen gene and pathway evaluations.",
        "Table5_orthogonal_final_status.tsv": "Orthogonal evidence and deterministic final status.",
        "S1_biological_unit_registry.tsv": "Biological-unit and accession registry.",
        "S2_per_library_QC.tsv": "Per-library discovery QC.",
        "S3_all_discovery_statistics.tsv": "Genome-wide discovery statistics.",
        "S4_robustness_file_manifest.tsv": "Internal robustness file manifest.",
        "S5_all_external_frozen_tests.tsv": "All external frozen tests.",
        "S6_pathway_signature_tests.tsv": "Pathway and signature tests.",
        "S7_DTU_results.tsv": "Conditional differential-transcript-usage results.",
        "S8_annotation_orthology.tsv": "Candidate annotation and orthology evidence.",
        "S9_small_RNA_results.tsv": "Small-RNA reference-gate outcome.",
        "S10_motif_background_tests.tsv": "Motif/background tests and sensitivity results.",
        "S11_evidence_registry.tsv": "Accession-aware published-evidence registry.",
        "S12_scripts_environments_commands.tsv": "Scripts, environments, and command inventory.",
        "S13_amendment_deviation_log.tsv": "Protocol amendments and deviations.",
    }
    items: list[tuple[str, str]] = []
    for directory in (ROOT / "results/tables", ROOT / "results/supplement"):
        for path in sorted(directory.glob("*.tsv")):
            with path.open(encoding="utf-8", errors="replace") as handle:
                rows = max(sum(1 for _ in handle) - 1, 0)
            relative = path.relative_to(ROOT)
            items.append(
                (
                    str(relative),
                    f"{descriptions.get(path.name, 'Electronic evidence table')} Rows: {rows:,}.",
                )
            )
    return items


def apply_species_italics(path: Path, terms: tuple[str, ...]) -> None:
    """Split DOCX runs so only Latin names, rather than whole paragraphs, are italic."""
    with zipfile.ZipFile(path) as archive:
        document_xml = archive.read("word/document.xml")
        members = [(item, archive.read(item.filename)) for item in archive.infolist()]

    for _, namespace in ET.iterparse(io.BytesIO(document_xml), events=("start-ns",)):
        prefix, uri = namespace
        if prefix != "xml":
            ET.register_namespace(prefix or "", uri)
    root = ET.fromstring(document_xml)
    ordered_terms = tuple(sorted(terms, key=len, reverse=True))
    split_pattern = re.compile("(" + "|".join(re.escape(term) for term in ordered_terms) + ")")

    for paragraph in root.findall(f".//{{{WORD_NS}}}p"):
        for run in list(paragraph.findall(f"{{{WORD_NS}}}r")):
            text_nodes = run.findall(f"{{{WORD_NS}}}t")
            if len(text_nodes) != 1:
                continue
            value = text_nodes[0].text or ""
            if not any(term in value for term in ordered_terms):
                continue
            run_properties = run.find(f"{{{WORD_NS}}}rPr")
            if run_properties is None:
                run_properties = ET.Element(f"{{{WORD_NS}}}rPr")
                run.insert(0, run_properties)
            for tag in ("i", "iCs"):
                node = run_properties.find(f"{{{WORD_NS}}}{tag}")
                if node is not None:
                    run_properties.remove(node)

            position = list(paragraph).index(run)
            paragraph.remove(run)
            for offset, segment in enumerate(part for part in split_pattern.split(value) if part):
                replacement = copy.deepcopy(run)
                replacement_text = replacement.find(f"{{{WORD_NS}}}t")
                replacement_text.text = segment
                if segment[:1].isspace() or segment[-1:].isspace():
                    replacement_text.set(f"{{{XML_NS}}}space", "preserve")
                replacement_properties = replacement.find(f"{{{WORD_NS}}}rPr")
                if segment in ordered_terms:
                    ET.SubElement(replacement_properties, f"{{{WORD_NS}}}i")
                    ET.SubElement(replacement_properties, f"{{{WORD_NS}}}iCs")
                paragraph.insert(position + offset, replacement)

    rewritten_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    temporary = path.with_suffix(".italic-fix.docx")
    with zipfile.ZipFile(temporary, "w") as archive:
        for item, payload in members:
            archive.writestr(
                item,
                rewritten_xml if item.filename == "word/document.xml" else payload,
            )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--manuscript", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, default=2002)
    args = parser.parse_args()

    template = args.template.resolve()
    manuscript = args.manuscript.resolve()
    output = args.output.resolve()
    if template == output:
        raise ValueError("Refusing to overwrite the legacy template")
    for path in (template, manuscript):
        if not path.is_file():
            raise FileNotFoundError(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    title, blocks = parse_markdown(manuscript)
    desktop = connect(args.port)
    document = desktop.loadComponentFromURL(
        uno.systemPathToFileUrl(str(template)),
        "_blank",
        0,
        (property_value("Hidden", True),),
    )
    if document is None:
        raise RuntimeError("LibreOffice could not load the legacy DOCX")

    try:
        builder = WriterBuilder(document)
        builder.clear_body()
        properties = document.DocumentProperties
        properties.Title = title
        properties.Author = "Eric Zhuang"
        properties.Subject = "Genome-wide lychee discovery and cross-context validation"
        properties.Description = (
            "Validated discovery/validation manuscript integrated into the legacy viXra formatting shell."
        )

        builder.paragraph(
            title,
            "Title",
            align=CENTER,
            font_size=16.0,
            bold=True,
            first_indent=0,
            after=240,
        )
        builder.paragraph(
            "Eric Zhuang",
            "Standard",
            align=CENTER,
            font_size=11.0,
            first_indent=0,
            after=260,
        )

        with tempfile.TemporaryDirectory(prefix="lychee_vixra_figures_") as temporary:
            temporary_dir = Path(temporary)
            abstract_seen = False
            inventory_inserted = False
            for kind, payload in blocks:
                if kind == "heading2":
                    heading = str(payload)
                    if heading == "Abstract":
                        abstract_seen = True
                    if heading == "Introduction" and abstract_seen:
                        builder.paragraph(
                            "Keywords: lychee; Litchi chinensis; Peronophythora litchii; "
                            "RNA-seq; genome-wide interaction; cross-context validation; "
                            "transcript usage; reproducibility",
                            "Body Text Indent1",
                            align=BLOCK,
                            font_size=10.5,
                            first_indent=0,
                            after=220,
                        )
                    if heading == "References" and not inventory_inserted:
                        builder.heading("Electronic supplementary data", 3)
                        builder.paragraph(
                            "The complete machine-readable tables are distributed with the repository and "
                            "are not embedded in this DOCX because several contain thousands to hundreds "
                            "of thousands of rows. Every item is checksum-covered by the release bundle.",
                            first_indent=635,
                        )
                        inventory = [["Artifact", "Contents"]]
                        inventory.extend([[path, description] for path, description in artifact_inventory()])
                        builder.table(
                            "Electronic supplementary data inventory.", inventory, font_size=7.5
                        )
                        inventory_inserted = True
                    builder.heading(heading, 2)
                elif kind == "heading3":
                    builder.heading(str(payload), 3)
                elif kind == "paragraph":
                    builder.paragraph(str(payload), first_indent=635)
                elif kind == "reference":
                    builder.paragraph(
                        str(payload),
                        "List Paragraph",
                        align=LEFT,
                        font_size=9.5,
                        first_indent=-500,
                        after=80,
                    )
                elif kind == "image":
                    info = dict(payload)
                    builder.image(Path(info["path"]), str(info["caption"]), temporary_dir)
                else:
                    raise ValueError(f"Unknown manuscript block: {kind}")

        builder.heading("Tables", 2)
        roles = read_tsv(ROOT / "results/tables/Table1_dataset_roles_eligibility.tsv")
        role_rows = [["Accession", "Design", "Role", "Eligibility"]]
        role_rows.extend(
            [[row["accession"], row["design"], row["role"], row["eligibility"]] for row in roles]
        )
        builder.table(
            "Table 1. Locked dataset roles and eligibility (condensed from electronic Table 1).",
            role_rows,
            font_size=7.2,
        )

        metrics = read_tsv(
            ROOT / "docs/paper/discovery_validation_manuscript/manuscript_metrics.tsv"
        )
        metric_rows = [["Metric", "Value"]]
        metric_rows.extend([[row["metric"].replace("_", " "), row["value"]] for row in metrics])
        builder.table("Table 2. Key validated computational outcomes.", metric_rows, font_size=8.5)

        tiers = read_tsv(ROOT / "results/candidates/tier_summary.tsv")
        tier_rows = [["Tier/status", "Count"]]
        tier_rows.extend([[row["tier"], row["count"]] for row in tiers])
        builder.table("Table 3. Deterministic final tier distribution.", tier_rows, font_size=9.0)

        document.storeAsURL(
            uno.systemPathToFileUrl(str(output)),
            (
                property_value("FilterName", "Office Open XML Text"),
                property_value("Overwrite", True),
            ),
        )
    finally:
        document.close(True)

    apply_species_italics(
        output, ("Litchi chinensis", "Peronophythora litchii", "P. litchii")
    )

    print(f"integrated_docx={output}")
    print(f"bytes={output.stat().st_size}")
    print(f"sha256={sha256(output)}")


if __name__ == "__main__":
    main()
