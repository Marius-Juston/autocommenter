import os
import ast

def extract_classes_and_functions(file_content):
    """
    Extract classes and functions from the provided Python file content.

    Args:
        file_content (str): The content of the Python file.

    Returns:
        dict: A dictionary with class and function names as keys and their definitions as values.
    """
    tree = ast.parse(file_content)
    result = {"classes": {}, "functions": {}}

    for node in ast.walk(tree):
        data = {}

        if isinstance(node, ast.ClassDef):
            data['source'] = ast.get_source_segment(file_content, node)
            data['doc'] = ast.get_docstring(node)
            data['line'] = node.body[0].lineno

            result["classes"][node.name] = data
        elif isinstance(node, ast.FunctionDef):
            data['source'] = ast.get_source_segment(file_content, node)
            data['doc'] = ast.get_docstring(node)
            data['line'] = node.body[0].lineno

            result["functions"][node.name] = data

    return result

def read_file(file_path):
    """
    Read the content of a file.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The content of the file.
    """
    with open(file_path, "r") as file:
        return file.read()

def find_python_files(folder_path):
    """
    Find all Python files in the specified folder and its subfolders.

    Args:
        folder_path (str): The path to the folder.

    Returns:
        list: A list of file paths to Python files.
    """
    python_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))
    return python_files

def main(folder_path):
    """
    Main function to find Python files in the folder and extract classes and functions.

    Args:
        folder_path (str): The path to the folder.
    """
    python_files = find_python_files(folder_path)

    for file_path in python_files:
        print(f"\nProcessing file: {file_path}")
        file_content = read_file(file_path)
        extracted_content = extract_classes_and_functions(file_content)

        for class_name, class_def in extracted_content["classes"].items():
            print(f"\nClass: {class_name}\n{class_def}")

        for func_name, func_def in extracted_content["functions"].items():
            print(f"\nFunction: {func_name}\n{func_def}")

if __name__ == "__main__":
    main('codebases')
