import re
from io import BytesIO

from magic_pdf.libs.MakeContentConfig import DropMode
from magic_pdf.pipe.UNIPipe import UNIPipe
from werkzeug.datastructures import FileStorage

from magic_doc.contrib.pdf.pdf_extractor import PDFExtractor
from magic_doc.conv.base import BaseConv
from magic_doc.model.doc_analysis import DocAnalysis, load_images_from_pdf
from magic_doc.progress.filepupdator import FileBaseProgressUpdator
from magic_doc.utils.null_writer import NullWriter

remove_img_pattern = re.compile(r"!\[.*?\]\(.*?\)")


NULL_IMG_DIR = "/tmp"


class SingletonModelWrapper:
    _instance = None

    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super(SingletonModelWrapper, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        self.doc_analysis = DocAnalysis()

    def __call__(self, bytes: bytes):
        images = load_images_from_pdf(bytes)
        return self.doc_analysis(images)


class Pdf(BaseConv):
    def to_md(self, bits: bytes | str) -> str:
        model_proc = SingletonModelWrapper()
        self._progress_updator.update(0)

        model_list = model_proc(bits)  # type: ignore
        self._progress_updator.update(50)
        jso_useful_key = {
            "_pdf_type": "",
            "model_list": model_list,
        }
        image_writer = NullWriter()
        pipe = UNIPipe(bits, jso_useful_key, image_writer, is_debug=True)  # type: ignore
        pipe.pipe_classify()
        pipe.pipe_parse()
        self._progress_updator.update(90)

        md_content = pipe.pipe_mk_markdown(NULL_IMG_DIR, drop_mode=DropMode.NONE)
        self._progress_updator.update(100)

        no_img_md_content = re.sub(remove_img_pattern, "", md_content)  # type: ignore
        no_img_md_content = re.sub(r"^\s\s\n", "", no_img_md_content,flags=re.MULTILINE)
        return no_img_md_content


if __name__ == "__main__":
    with open("/opt/data/pdf/20240423/pdf_test2/ol006018w.pdf", "rb") as f:
        bits_data = f.read()
        parser = Pdf(FileBaseProgressUpdator("debug/progress.txt"))
        md_content = parser.to_md(bits_data)

        with open("debug/pdf2md.by_model.md", "w") as f:
            f.write(md_content)