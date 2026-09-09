from pathlib import Path

from paddleocr import PaddleOCR
from image_preprocess import crop_label, preprocess_image


ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
)

def run_ocr(image_path: str):
    """
    Run PaddleOCR and return detected text plus confidence.
    """

    results = ocr.predict(image_path)

    detected = []

    for result in results:

        try:
            data = result.json

            if callable(data):
                data = data()

        except Exception:
            data = None

        if not data:

            try:
                data = dict(result)

            except Exception:
                continue

        if "res" in data:
            data = data["res"]

        texts = data.get(
            "rec_texts",
            []
        )

        scores = data.get(
            "rec_scores",
            []
        )

        for index, text in enumerate(texts):

            text = str(text).strip()

            if not text:
                continue

            score = None

            if index < len(scores):

                try:
                    score = float(
                        scores[index]
                    )

                except Exception:
                    score = None

            detected.append(
                {
                    "text": text,
                    "confidence": score,
                }
            )

    return detected

def identify_card(image_path: str):

    image_path = str(
        Path(image_path)
    )

    print()
    print("Reading card:")
    print(image_path)
    print()

    crop_path = crop_label(
        image_path,
        "results/label_crop.jpg",
    )

    lines = run_ocr(
        crop_path
    )

    if len(lines) < 3:

        processed_path = preprocess_image(
            crop_path,
            "label_processed.jpg",
        )

        processed_lines = run_ocr(
            processed_path
        )

        if (
            len(processed_lines)
            > len(lines)
        ):
            lines = processed_lines

    valid_scores = [
        x["confidence"]
        for x in lines
        if x["confidence"] is not None
    ]

    if valid_scores:

        average_confidence = (
            sum(valid_scores)
            / len(valid_scores)
        )

    else:
        average_confidence = None

    result = {
        "ocr_confidence": average_confidence,
        "raw_ocr": lines,
    }

    return result

def print_ocr_results(card_result):
    print()
    print("OCR Results:")

    for item in card_result["raw_ocr"]:
        text = item["text"]
        confidence = item["confidence"]

        if confidence is not None:
            print(f"{text:<30} {confidence:.2%}")
        else:
            print(text)