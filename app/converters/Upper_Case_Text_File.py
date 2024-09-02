def convert_text_to_uppercase(input_path: str, output_path: str):

    with open(input_path, "r") as f:
        text = f.read()

    with open(output_path, "w") as f:
        f.write(text.upper())
