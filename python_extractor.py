import ast
import hashlib
import os
from copy import deepcopy
from enum import Enum
from typing import Union, Dict, Optional

import black
from langchain_community.llms.ollama import Ollama
from langchain_core.prompts import ChatPromptTemplate


class Type(Enum):
    FUNCTIONS = 0
    CLASSES = 1


class ParentClassFinder(ast.NodeVisitor):
    def __init__(self):
        self.parent_classes = {}
        self.current_class = None

    def visit_ClassDef(self, node):
        self.current_class = node
        self.parent_classes[node] = None
        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, node):
        if self.current_class:
            self.parent_classes[node] = self.current_class
        else:
            self.parent_classes[node] = None
        self.generic_visit(node)


class PythonExtractor:
    def __init__(self, root_directory: str | os.PathLike):
        self.root_directory = root_directory

        self.template_message = 'This is an autogenerated docstring'

        self.ai_documenter = AIDocumenter()

    def extract_classes_and_functions(self, file_content):
        """
        Extract classes and functions from the provided Python file content.

        Args:
            file_content (str): The content of the Python file.

        Returns:
            dict: A dictionary with class and function names as keys and their definitions as values.
        """
        tree = ast.parse(file_content)

        finder = ParentClassFinder()
        finder.visit(tree)

        nodes = {}

        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                data = {}

                data['source'] = ast.get_source_segment(file_content, node)
                data['doc'] = ast.get_docstring(node)
                data['node'] = node

                type = Type.CLASSES if isinstance(node, ast.ClassDef) else Type.FUNCTIONS
                data['type'] = type

                data['parent'] = finder.parent_classes[node]

                nodes[node] = data

        for n in nodes:
            parent_node = nodes[n]['parent']

            if parent_node:
                nodes[n]['parent_source'] = nodes[parent_node]['source']
            else:
                nodes[n]['parent_source'] = None

        return tree, nodes

    def read_file(self, file_path):
        """
        Read the content of a file.

        Args:
            file_path (str): The path to the file.

        Returns:
            str: The content of the file.
        """
        with open(file_path, "r") as file:
            return file.read()

    def find_python_files(self, folder_path):
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

    def get_docstring(self, node: Union[ast.ClassDef, ast.FunctionDef]):
        """
        Get the docstring of a given AST node.

        Args:
            node (ast.AST): The AST node to extract the docstring from.

        Returns:
            str: The extracted docstring or an empty string if not present.
        """
        return ast.get_docstring(node)

    def set_docstring(self, node: Union[ast.ClassDef, ast.FunctionDef], docstring):
        """
        Set the docstring for a given AST node.

        Args:
            node (ast.AST): The AST node to set the docstring for.
            docstring (str): The docstring to set.
        """
        docstring_node = ast.Expr(value=ast.Constant(value=docstring))
        node.body.insert(0, docstring_node)

    def update_docstring(self, node: Union[ast.ClassDef, ast.FunctionDef], docstring):
        """
        Update the docstring for a given AST node.

        Args:
            node (ast.AST): The AST node to set the docstring for.
            docstring (str): The docstring to set.
        """
        docstring_node = ast.Expr(value=ast.Constant(value=docstring))
        node.body[0] = docstring_node

    def extract(self):
        """
        Main function to find Python files in the folder and extract classes and functions.

        Args:
            folder_path (str): The path to the folder.
        """
        python_files = self.find_python_files(self.root_directory)

        for file_path in python_files:
            print(f"\nProcessing file: {file_path}")
            file_content = self.read_file(file_path)

            tree, extracted_content = self.extract_classes_and_functions(file_content)

            modified = False

            for func_node in extracted_content.values():
                modified = self.generate_doc(func_node) or modified

            if modified:
                new_content = ast.unparse(tree)

                formatted_new_content = black.format_str(new_content, mode=black.Mode())

                self.write_file(file_path, formatted_new_content)

    def write_file(self, file_path, content):
        """
        Write content to a file.

        Args:
            file_path (str): The path to the file.
            content (str): The content to write.
        """
        with open(file_path, "w") as file:
            file.write(content)

    def generate_func_hash(self, node: ast.AST, has_documentation=False):

        if has_documentation:
            node: ast.AST = deepcopy(node)
            # Remove the documentation when generating the hash, you only care about the contents of the function
            node: Union[ast.ClassDef, ast.FunctionDef]

            del node.body[0]

        # Convert the AST node to a string representation
        node_str = ast.dump(node)

        # Create a SHA-256 hash object
        hash_object = hashlib.sha256()

        # Update the hash object with the bytes of the node string
        hash_object.update(node_str.encode('utf-8'))

        # Return the hexadecimal digest of the hash
        return hash_object.hexdigest()

    def generate_doc(self, node: Dict):
        class_node: Union[ast.ClassDef, ast.FunctionDef] = node['node']

        node_type: str = node['type']

        print(f"Working on {node_type}: {class_node.name}", f"from {node['parent'].name}" if node['parent'] else "")

        documentation = self.get_docstring(class_node)

        hash = self.generate_func_hash(class_node, has_documentation=not (documentation is None))

        modified = False

        if documentation and self.template_message in documentation:
            if node_type == Type.FUNCTIONS:

                previous_hash = documentation.split(' ')[-1].strip()

                if not (previous_hash == hash):
                    print(
                        "There is a hash mismatch between the function and the last time the documentation for it was generated.")

                    text = self.api_find_docstring(node)

                    text = self.parse_doc(text, hash)

                    self.update_docstring(class_node, text)

                    modified = True
        if not documentation:
            text = self.api_find_docstring(node)
            text = self.parse_doc(text, hash)

            self.set_docstring(class_node, text)

            modified = True

        return modified

    def parse_doc(self, text: str, hash: str):

        return os.linesep.join([
            "",
            text,
            "",
            self.template_message,
            f'hash {hash}',
            ""
            ""
        ])

    def api_find_docstring(self, node):
        docstring = self.ai_documenter(node['source'], node['type'], node['parent_source'])

        print(docstring)

        return docstring


class AIDocumenter:
    def __init__(self):
        # model = Ollama(model="dolphin-mistral")
        self.model = Ollama(model="codestral")
        self.model.num_ctx = 32768

        function_documentation_template = """
Class Context:
{context}
        
Write comprehensive documentation for the following Python code using reStructuredText (reST) format. The documentation should include a description, parameter explanations, return type, and examples. Ensure the documentation is clear, concise, and follows standard conventions. If the function is from a class use that context to improve the description.

Example output:
Function <Function Name>
========================

Description
-----------
<Brief description of the function's purpose.>

Parameters
----------
- a (int): <Explanation of the first parameter.>
- b (int): <Explanation of the second parameter.>

Returns
-------
- int: <Explanation of the return type.>

Examples
--------
.. code-block:: python

    <Example 1>

    <Example 2>

Notes
-----
<Any additional notes or caveats.>

Function:
{function}

Documentation:
"""

        class_documentation_template = """
Write comprehensive header documentation for the following Python class using reStructuredText (reST) format. The documentation should include a description, attribute explanations, method summaries, inheritance diagrams, and examples. Ensure the documentation is clear, concise, and follows standard conventions.

<Class Name>
============

Description
-----------
<Brief description of the class's purpose.>

Attributes
----------
- attribute_name (type): <Explanation of the attribute.>

Methods
-------
- method_name(parameters): <Brief description of the method.>

Examples
--------
.. code-block:: python

    <Example 1>

    <Example 2>

Notes
-----
<Any additional notes or caveats.>

Class:
{function}

Documentation:
"""

        func_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    function_documentation_template,
                )
            ]
        )

        class_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    class_documentation_template,
                )
            ]
        )

        self.function_chain = func_prompt | self.model
        self.class_chain = class_prompt | self.model

        self.chain = {Type.FUNCTIONS: self.function_chain, Type.CLASSES: self.class_chain}

    def normalize_left_strip(self, txt: str, type: str):
        lines = txt.split(os.linesep)

        line_strip = None

        for i, line in enumerate(lines):
            lines_stripped = line.lstrip()

            for mixes in ['====', '----']:
                if lines_stripped.startswith(mixes):
                    index = line.find(mixes)

                    if line_strip:
                        line_strip = min(index, line_strip)
                    else:
                        line_strip = index

                    if i > 0:
                        prev_line = lines[i - 1].strip()

                        if Type.FUNCTIONS == type and '====' in line:
                            if not (' ' in prev_line):
                                first_char_index = prev_line.index(prev_line[0])

                                lines[i - 1] = lines[i - 1][:first_char_index] + "Function " + lines[i - 1][
                                                                                               first_char_index:]

                                prev_line = lines[i - 1].strip()

                        num_characters = len(prev_line)

                        current_line = line.strip()

                        if len(prev_line) > len(current_line):
                            characters = current_line[0] * num_characters

                            lines[i] = lines[i][:index] + characters

        if not line_strip:
            return txt

        for i in range(len(lines)):
            first_char = lines[i].lstrip()

            if len(first_char) == 0:
                continue

            text_index = lines[i].find(first_char[0])

            max_stripping = min(line_strip, text_index)

            lines[i] = lines[i][max_stripping:]

        return os.linesep.join(lines)

    def __call__(self, function_source: str, type: str, parent_source: Optional[str]):

        template_input = {"function": function_source}

        chain = self.chain[type]

        if type == Type.FUNCTIONS:
            # print(self.model.get_num_tokens(function_source), self.model.get_num_tokens(parent_source))

            if parent_source:
                # python_splitter = RecursiveCharacterTextSplitter.from_language(
                #     language=Language.PYTHON, chunk_size=50, chunk_overlap=0
                # )
                # python_docs = python_splitter.create_documents([PYTHON_CODE])

                template_input['context'] = parent_source
            else:
                template_input['context'] = "This function is not part of a class."

        response = chain.invoke(
            template_input
        ).strip()

        response = self.normalize_left_strip(response)

        return response


if __name__ == '__main__':
    data = PythonExtractor('codebases/apecs_library')

    data.extract()
