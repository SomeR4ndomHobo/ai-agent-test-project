import cv2


def crop_label(
    image_path: str,
    output_path: str = "f{image_path}/label_crop.jpg"
):
    """
    Crop the top portion of a graded-card slab.

    This assumes the grading label occupies approximately
    the top 30% of the photograph.
    """

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(
            f"Could not open image: {image_path}"
        )

    height, width = image.shape[:2]

    label_height = int(height * 0.30)

    label = image[
        0:label_height,
        0:width
    ]

    label = cv2.resize(
        label,
        None,
        fx=2,
        fy=2,
        interpolation=cv2.INTER_CUBIC,
    )

    cv2.imwrite(
        output_path,
        label
    )

    return output_path


def preprocess_image(
    image_path: str,
    output_path: str = "label_processed.jpg"
):
    """
    Create a high-contrast version of the label.

    This version is used only if the normal image
    produces poor OCR results.
    """

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(
            f"Could not open image: {image_path}"
        )

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    gray = cv2.GaussianBlur(
        gray,
        (3, 3),
        0
    )

    processed = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        10,
    )

    cv2.imwrite(
        output_path,
        processed
    )

    return output_path