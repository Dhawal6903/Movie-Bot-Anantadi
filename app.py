from flask import Flask, request, jsonify, render_template
import openai
import pinecone
import json
from flask_cors import CORS
import pandas as pd
from RagModel import SelfQueryRetriever, format_docs, retriever, rag_chain_with_source,query_constructor  # Ensure you import your RAG model
import os
import csv
import pandas as pd
from pinecone import Pinecone, PodSpec
from langchain_pinecone import PineconeVectorStore
from langchain.indexes import SQLRecordManager, index
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
import os
import csv
import pandas as pd
from pinecone import Pinecone, PodSpec
from langchain_pinecone import PineconeVectorStore
from langchain.indexes import SQLRecordManager, index
from langchain_openai import OpenAIEmbeddings
from langchain.chains.query_constructor.base import AttributeInfo
from langchain_openai import (
    ChatOpenAI, 
    OpenAIEmbeddings
)
from langchain.chains.query_constructor.base import (
    StructuredQueryOutputParser,
    get_query_constructor_prompt,
    AttributeInfo
)
import lark
from langchain.llms import OpenAI
from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain.retrievers.self_query.pinecone  import PineconeTranslator
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables import RunnableParallel
from langchain_openai import ChatOpenAI

PINECONE_KEY =  "%%%%%%"
PINECONE_INDEX_NAME =  'moviefy'
OPENAI_KEY =  "%%%%%"

document_content_description = "Brief overview of a movie, along with keywords"
def format_docs(docs):
    return "\n\n".join(f"{doc.page_content}\n\nMetadata: {doc.metadata}" for doc in docs)


# Define allowed comparators list
allowed_comparators = [
    "$eq",  # Equal to (number, string, boolean)
    "$ne",  # Not equal to (number, string, boolean)
    "$gt",  # Greater than (number)
    "$gte",  # Greater than or equal to (number)
    "$lt",  # Less than (number)
    "$lte",  # Less than or equal to (number)
    "$in",  # In array (string or number)
    "$nin",  # Not in array (string or number)
]

examples = [
    (
        "I'm looking for a sci-fi comedy released after 2021.",
        {
            "query": "sci-fi comedy",
            "filter": "and(eq('Genre', 'Science'), eq('Genre', 'Comedy'), gt('Release Year', 2021))",
        },
    ),
    (
        "Show me critically acclaimed dramas without Tom Hanks.",
        {
            "query": "critically acclaimed drama",
            "filter": "and(eq('Genre', 'Drama'), nin('Actors', ['Tom Hanks']))",
        },
    ),
    (
        "Recommend some films by Yorgos Lanthimos.",
        {
            "query": "Yorgos Lanthimos",
            "filter": 'in("Directors", ["Yorgos Lanthimos]")',
        },
    ),
    (
        "Films similar to Yorgos Lanthmios movies.",
        {
            "query": "Dark comedy, absurd, Greek Weird Wave",
            "filter": 'NO_FILTER',
        },
    ),
    (
        "Find me thrillers with a strong female lead released between 2015 and 2020.",
        {
            "query": "thriller strong female lead",
            "filter": "and(eq('Genre', 'Thriller'), gt('Release Year', 2015), lt('Release Year', 2021))",
        },
    ),
    (
        "Find me highly rated drama movies in English that are less than 2 hours long",
        {
            "query": "Highly rated drama English under 2 hours",
            "filter": 'and(eq("Genre", "Drama"), eq("Language", "English"), lt("Runtime (minutes)", 120))',
        },
    ),
]

metadata_field_info = [
    AttributeInfo(
        name="title",
        description="The title of the movie",
        type="string or list[string]",
    ),
    AttributeInfo(
        name="genres",
        description="Genre of the movie or category of the movie",
        type="string or list[string]",
    ),
    AttributeInfo(
        name="rating",
        description="A 1-10 rating for the movie",
        type="float",
    ),
    AttributeInfo(
        name="release_date", description="Release Date of the movie", type="string"
    ),
    AttributeInfo(
        name="popularity", description="popularity of the movie", type="float"
    ),
]
document_content_description = "Brief summary of a movie"

def create_response(input):
    constructor_prompt = get_query_constructor_prompt(
    document_content_description,
    metadata_field_info,
    allowed_comparators=allowed_comparators,
    examples=examples,
        )
    openai_key = "%%%%%%"
    query_model = ChatOpenAI(
            model='gpt-3.5-turbo-0125',
            temperature=0,
            streaming=True,api_key=openai_key
        )

    output_parser = StructuredQueryOutputParser.from_components()
    query_constructor = constructor_prompt | query_model | output_parser
    question = input
    query_constructor.invoke(
    {
        "query": question
    })  
    vectorstore=create_pinecone_index()
    retriever = SelfQueryRetriever(
    query_constructor=query_constructor,
    vectorstore=vectorstore,
    structured_query_translator=PineconeTranslator(),
    search_kwargs={'k': 10}
    )

    retriever.invoke(question)
    chat_model = ChatOpenAI(
    model='gpt-3.5-turbo-0125',
    # model='gpt-4-0125-preview',
    temperature=0,
    streaming=True,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                'system',
                """
                Your goal is to recommend films to users based on their 
                query and the retrieved context. If a retrieved film doesn't seem 
                relevant, omit it from your response. Never refer to films that
                are not in your context. If you cannot recommend any 
                films, suggest better queries to the user. You cannot 
                recommend more than five films. Your recommendation should 
                be relevant, original, and at least two to three sentences 
                long for each movie.
                
                YOU CANNOT RECOMMEND A FILM IF IT DOES NOT APPEAR IN YOUR 
                CONTEXT.

                # TEMPLATE FOR OUTPUT
                - [Title of Film](source link):
                    - Runtime:
                    - Release Year:
                    - (Your reasoning for recommending this film)
                    -Rating:
                    -Popularity:
                
                Question: {question} 
                Context: {context} 
                """
            ),
        ]
    )

    # Create a chatbot Question & Answer chain from the retriever
    rag_chain_from_docs = (
        RunnablePassthrough.assign(context=(lambda x: format_docs(x["context"])))
        | prompt
        | chat_model
        | StrOutputParser()
    )

    rag_chain_with_source = RunnableParallel(
        {"context": retriever, "question": RunnablePassthrough()}
    ).assign(answer=rag_chain_from_docs)


    query_constructor.invoke(
        {
            "query": question
        }
    )
    # Only prints final answer
    # for chunk in rag_chain_with_source.stream(question):
    #     for key in chunk:
    #         if key == 'answer':
    #             print(chunk[key], end="", flush=True)

    # Prints everything
    output = {}
    curr_key = None
    for chunk in rag_chain_with_source.stream(question):
        for key in chunk:
            if key not in output:
                output[key] = chunk[key]
            else:
                output[key] += chunk[key]
            if key != curr_key:
                print(f"\n\n{key}: {chunk[key]}", end="", flush=True)
            else:
                print(chunk[key], end="", flush=True)
            curr_key = key
    return output

def create_pinecone_index():
            # Initialize Pinecone with API key
            pc = Pinecone(api_key=PINECONE_KEY)

            # Create Pinecone index if not exists
            # pc.create_index(
            #     name=PINECONE_INDEX_NAME,
            #     dimension=1536,
            #     metric="cosine",
            #     spec=PodSpec(
            #         environment="gcp-starter"
            #     )
            # )

            # Target the existing index and check its status
            pc_index = pc.Index(PINECONE_INDEX_NAME)
            print(pc_index.describe_index_stats())

            # Initialize OpenAI embeddings with API key
            embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", api_key=OPENAI_KEY)

            # Read CSV file
            csv_file_path = "cleaned_tmdb.csv"
            df = pd.read_csv(csv_file_path)

            # Define the documents list
            docs = []
            for index, row in df.iterrows():
                document = Document(
                page_content=row["overview"],  # Assuming "overview" column contains text content
                metadata={
                "title": row["title"],  # Assuming "title" column contains movie title
                "poster_path": row["poster_path"],
                "rating": row["rating"],
                "popularity": row["popularity"], 
                "release_date": row["release_date"],
                "genres": row["genres"],

                }
                )
                docs.append(document)

            # Create Pinecone vector store from documents
            vectorstore = PineconeVectorStore.from_documents(
                docs, embeddings, index_name=PINECONE_INDEX_NAME
            )

            print("Pinecone vector store created successfully.")
            return vectorstore

def serialize_document(doc):
    return {
        "page_content": doc.page_content,
        "metadata": doc.metadata
    }
app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

# API route for getting recommendations
@app.route('/get_recommendations', methods=['POST'])
def get_recommendations():
    if request.is_json:
        data = request.get_json()
        print(data)
        answer = create_response(data.get("question", None))
        
        # Serialize the documents in the answer
        serialized_answer = {
            key: [serialize_document(doc) for doc in value] if isinstance(value, list) else value
            for key, value in answer.items()
        }
        
        return jsonify(serialized_answer), 200

if __name__ == '__main__':
    app.run(debug=True)
