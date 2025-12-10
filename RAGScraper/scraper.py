from bs4 import BeautifulSoup, NavigableString, Tag
from requests.api import get
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI
import requests
import math
import os
import re

load_dotenv()

openai = OpenAI()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index("ie421-group10")

objects_arr = []
object_attrs_arr = []

def get_embeddings(texts):

    response = openai.embeddings.create(
        model="text-embedding-3-small",  # 1536 dims
        input=texts
    )

    embeddings = [d.embedding for d in response.data]
    return embeddings

def format_object_embedding(class_name, desc):

    text = f"""
    className: {class_name}
    description: {desc}
    """

    metadata = {
        "className": class_name,
        "text": text
    }

    id = class_name

    return text, metadata, id

def add_object_embeddings():

    global objects_arr

    num_batches = math.ceil(len(objects_arr) / 100)
    for i in range(0, len(objects_arr), 100):

        print(f"[Processing] batch {i // 100}/{num_batches}")
        
        batch = objects_arr[i:i+100]
        texts = [text for (text, _, _) in batch]

        embeddings = get_embeddings(texts)

        vectors = [{ "id": id, "values": embedding, "metadata": metadata } for (_, metadata, id), embedding in zip(batch, embeddings)]

        index.upsert(
            vectors=vectors,
            namespace="objects"
        )

def get_object(suffix):

    global objects_arr

    url = f"https://help.autodesk.com{suffix}"

    rsp = requests.get(url)
    rsp.raise_for_status()

    soup = BeautifulSoup(rsp.text, "html.parser")

    # print(soup.prettify())

    object = soup.find("meta", attrs={"name": "contextid"})
    object_name = object.get("content")

    print(f"[Extarcting] {object_name}")

    desc_h2 = soup.select_one("h2.api")

    parts = []
    for el in desc_h2.next_elements:

        if isinstance(el, Tag) and el.name == "h2" and "api" in (el.get("class") or []):
            break

        if isinstance(el, NavigableString):
            
            text = el.strip()
            
            if text:
                parts.append(text)

    desc = " ".join(parts)
    
    res = format_object_embedding(object_name, desc)
    objects_arr.append(res)

def get_object_attr(suffix):

    global object_attrs_arr

    url = f"https://help.autodesk.com{suffix}"

    rsp = requests.get(url)
    rsp.raise_for_status()

    soup = BeautifulSoup(rsp.text, "html.parser")

    print(soup.prettify())

    # Description
    description = soup.select_one("p.api").contents[0]

    # Syntax
    python_div = soup.select_one("div#Python")

    var_context = python_div.select_one("td")

    var_context_text = None
    for child in var_context.children:
        if isinstance(child, NavigableString):
            text = child.strip()
            if text:
                var_context_text = text
                break

    code = python_div.select_one("pre.api-code")
    
    pieces = []
    for node in code.descendants:
        
        if isinstance(node, Tag) and node.name == "br":
            pieces.append("\n")
        
        elif isinstance(node, NavigableString):
            
            text = str(node).replace("\n", "")
            
            if text:
                pieces.append(text)

    code_text = "".join(pieces).strip()
    
    # Return Value



    # Parameters

    params_h2 = soup.find("h2", class_="api", string=re.compile(r"\s*Property Value\s*"))

    type = None
    for el in params_h2.next_elements:
        
        if isinstance(el, NavigableString):
            
            text = el.strip()
            match = re.match(r"This is a (read|write|read/write) property whose value is a (.+)\.", text)
            
            if match:
                type = match.group(2)  
                break      

    print(type)


def get_objects(content):

    if "children" in content:
        
        suffix = content["ln"]

        if suffix != "":
            get_object(suffix)
        
        for child in content["children"]:
            get_objects(child)

if __name__ == "__main__":

    # Hidden API 

    # url = "https://help.autodesk.com/view/fusion360/ENU/data/toctree.json"

    # # Returns sidebar elements and their nested children
    # # Each (leaf) children has property ln which is a relative link to its docs

    # rsp = requests.get(url)
    # json_content = rsp.json()

    # objects = json_content["books"][20]["children"][3]["children"][0]

    # get_objects(objects)
    # add_object_embeddings()

    # enums = json_content["books"][20]["children"][3]["children"][1]
    # samples = json_content["books"][20]["children"][4]

    url = "/cloudhelp/ENU/Fusion-360-API/files/AdditiveFFFLimitsMachineElement_maximumXYSpeed.htm"
    # url = "/cloudhelp/ENU/Fusion-360-API/files/ActiveSelectionEvent.htm"

    get_object_attr(url)