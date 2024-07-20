from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate

if __name__ == '__main__':
    model = Ollama(model="dolphin-mistral")

    function_documentation_template = """
    Given the following Python function or Class, generate comprehensive documentation including a description, parameters, and return value in reStructredText format.

    Function:
    {function}

    Documentation:
    """

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                function_documentation_template,
            )
        ]
    )

    chain = prompt | model

    # Example usage
    example_function = """
    def add_numbers(a, b):
        \"\"\"Adds two numbers.\"\"\"
        return a + b
    """

    response = chain.invoke(
        {"function": example_function}
    )

    print(response)
