from bs4 import BeautifulSoup, NavigableString, Tag
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI
import requests
import math
import json
import os
import re

load_dotenv()

openai = OpenAI()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index("ie421-group10")

# Get Description

def gen_description(description, code):

    prompt = f"""
    You are a Fusion 360 expert. Your task is to generate a concise, high-quality description (one paragraph) of the provided Fusion 360 demo code for use in a RAG system.

    Use the official Fusion 360 documentation description below to understand the code's purpose:
    {description}

    Analyze the following code and produce an enhanced technical description that clearly explains what the script does, how it interacts with the Fusion 360 API, and the operations it performs:
    Python
    {code}

    Constraints:
    - Output only the enhanced description of the code.
    - Do not exceed one paragraphs.
    - Do not include any additional commentary or formatting.
    """.strip()

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a Fusion 360 expert that generates clear, technical descriptions for RAG applications."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=300,
        temperature=0.4,
        n=1,
    )

    return response.choices[0].message.content.strip()

# Embeddings

def get_embeddings(texts):

    response = openai.embeddings.create(
        model="text-embedding-3-small",  # 1536 dims
        input=texts
    )

    embeddings = [d.embedding for d in response.data]
    return embeddings

def add_embeddings(arr, namespace, batch_size=50):

    num_batches = math.ceil(len(arr) / batch_size)
    for i in range(0, len(arr), batch_size):

        print(f"[Processing] {namespace} batch {(i // batch_size) + 1}/{num_batches}")
        
        batch = arr[i:i+batch_size]
        texts = [text for (_, _, text) in batch]

        embeddings = get_embeddings(texts)

        vectors = [{ "id": id, "values": embedding, "metadata": metadata } for (id, metadata, _), embedding in zip(batch, embeddings)]

        index.upsert(
            vectors=vectors,
            namespace=namespace
        )

def format_sample_embedding(pairs):

    ttl, description, code = pairs.values()

    print(f"[GENERATING] enhanced description for {ttl}")
    enhanced_description = gen_description(description, code)

    text = f"""
    title: {ttl}
    description: {enhanced_description}
    """

    if len(text) + len(code) > 5 * 8192:
        return None

    metadata = {
        "text": text,
        "sampleId": ttl,
        "codeSample": code,
    }

    id = ttl

    return id, metadata, text

# Get Samples

def get_sample(ttl, ln):

    global samples_arr

    def get_description(soup):

        h2 = soup.find("h2", class_="api", string=re.compile(r"^\s*Description\s*$"))
        
        if not h2:
            return ""
        
        parts = []

        for el in h2.next_siblings:
            
            if isinstance(el, Tag) and el.name == "h2" and "api" in (el.get("class") or []):
                break

            if isinstance(el, NavigableString):
                
                text = el.strip()
                
                if text:
                    parts.append(text)

            elif isinstance(el, Tag):
                
                text = el.get_text(strip=True)
                
                if text:
                
                    parts.append(text)

        description = " ".join(parts).strip()
        return description

    def get_code(soup):

        code = soup.find("pre", id=f"Python_code")

        if code is None:
            return None

        for tag in code.find_all(["span"]):
            tag.unwrap()

        formatted_code = code.get_text("")

        return formatted_code

    url = f"https://help.autodesk.com{ln}"

    rsp = requests.get(url)
    rsp.raise_for_status()

    soup = BeautifulSoup(rsp.text, "html.parser")

    print(f"[EXTRACTING] {ttl} @ {ln}")

    description = get_description(soup)
    code = get_code(soup)

    if code is None:
        return

    pairs = {
        "ttl": ttl, 
        "description": description, 
        "code": code
    }

    res = format_sample_embedding(pairs)

    if res is None:
        return

    samples_arr.append(res)

start_sample = "Avoid Machine Surface Settings API Sample"
start_sample_found = False

def get_samples(content):

    global start_sample, start_sample_found

    if "children" in content:

        ttl = content["ttl"]
                
        for child in content["children"]:
            get_samples(child)

    else:

        ln = content["ln"]
        ttl = content["ttl"]

        start_sample_found = start_sample_found or start_sample == ttl

        if start_sample_found and ln != "":
            get_sample(ttl, ln)

# Get Objects

def format_object_embedding(pairs):

    class_name, description, methods_table, properties_table, samples_table = pairs.values()

    print(f"[GENERATING] description for {class_name}")

    text = f"""
    title: {class_name}
    description: {description}
    """

    metadata = {
        "text": text,
        "className": class_name,
        "sampleIds": samples_table,
        "methods": f"methods[{len(methods_table)}]{{name,description}}:\n{"\n\t".join(methods_table)}",
        "properties": f"properties[{len(properties_table)}]{{name,description}}:\n{"\n\t".join(properties_table)}"
    }

    id = class_name

    return id, metadata, text

def get_object(ttl, ln):

    global objects_arr

    def get_description(soup):

        h2 = soup.find("h2", class_="api", string=re.compile(r"^\s*Description\s*$"))
        
        if not h2:
            return ""
        
        parts = []

        for el in h2.next_siblings:
            
            if isinstance(el, Tag) and el.name == "h2" and "api" in (el.get("class") or []):
                break

            if isinstance(el, NavigableString):
                
                text = el.strip()
                
                if text:
                    parts.append(text)

            elif isinstance(el, Tag):
                
                text = el.get_text(strip=True)
                
                if text:
                
                    parts.append(text)

        description = " ".join(parts).strip()
        return description

    def get_table(h2, num_headers):

        table = h2.find_next("table")

        if not table:
            return []

        rows = table.find_all("tr")
        
        extracted = []
        for row in rows[1:]:
            
            values = row.find_all(["td"])
            
            if values[0].get_text(strip=True) in ["classType", "isValid", "objectType"]:
                continue

            vals = [values[i].get_text(strip=True) for i in range(num_headers)]
            extracted.append(",".join(vals))

        return extracted

    url = f"https://help.autodesk.com{ln}"

    rsp = requests.get(url)
    rsp.raise_for_status()

    soup = BeautifulSoup(rsp.text, "html.parser")

    print(f"[EXTRACTING] {ttl} @ {ln}")

    description = get_description(soup)

    methods_h2 = soup.find("h2", class_="api", string=re.compile(r"^\s*Methods\s*$"))

    methods_table = []
    if methods_h2:
        methods_table = get_table(methods_h2, 2)
        # print(methods_table)

    properties_h2 = soup.find("h2", class_="api", string=re.compile(r"^\s*Properties\s*$"))

    properties_table = []
    if properties_h2:
        properties_table = get_table(properties_h2, 2)
        # print(properties_table)

    samples_h2 = soup.find("h2", class_="api", string=re.compile(r"^\s*Samples\s*$"))

    samples_table = []
    if samples_h2:
        samples_table = get_table(samples_h2, num_headers=1)
        # print(samples_table)

    pairs = {
        "ttl": ttl,
        "description": description,
        "methods_table": methods_table,
        "properties_table": properties_table,
        "samples_table": samples_table,
    }

    res = format_object_embedding(pairs)

    if res is None:
        return

    objects_arr.append(res)

def format_object_attr_embedding(pairs):
    
    name, description, property_type, method_parameters, method_return_values, example_usage = pairs.values()

    print(f"[GENERATING] description for {name}")

    text = f"""
    title: {name}
    description: {description}
    """

    class_name, attr_name = name.split(".")

    method_params = f"methodParams[{len(method_parameters)}]{{name,type,description}}:\n{"\n\t".join(method_parameters)}" if len(method_parameters) != 0 else "N/A"
    method_return_vals = f"methodReturnVals[{len(method_return_values)}]{{name,description}}:\n{"\n\t".join(method_return_values)}" if len(method_return_values) != 0 else "N/A"

    metadata = {
        "text": text,
        "className": class_name,
        "attributeName": attr_name,
        "propertyType": property_type,
        "methodParams": method_params,
        "methodReturnVals": method_return_vals,
        "exampleUsage": f"Python\n{example_usage}"
    }

    id = name

    return id, metadata, text

def get_object_attr(ln):

    global object_attrs_arr

    def get_name(soup):
        
        h1_tag = soup.find("h1", class_="api")
        if not h1_tag:
            return ""
        
        name = h1_tag.get_text(strip=True).split(" ")[0]
        return name

    def get_content(h2):
        
        parts = []
        for el in h2.next_siblings:
            
            if isinstance(el, Tag) and el.name == "h2" and "api" in (el.get("class") or []):
                break

            if isinstance(el, NavigableString):
                
                text = el.strip()
                
                if text:
                    parts.append(text)

            elif isinstance(el, Tag):
                
                text = el.get_text(strip=True)
                
                if text:
                
                    parts.append(text)

        description = " ".join(parts).strip()
        return description

    def get_syntax(soup):

        div = soup.find("div", id="Python")

        if not div:
            return ""

        code = div.find_next("pre")

        if not code:
            return ""

        for tag in code.find_all(["span", "b", "em"]):
            tag.unwrap()

        for br in code.find_all("br"):
            br.replace_with("\n")

        formatted_code = code.get_text("")

        return formatted_code

    def get_table(h2, num_headers):

        table = h2.find_next("table")

        if not table:
            return []

        rows = table.find_all("tr")
        
        extracted = []
        for row in rows[1:]:
            
            values = row.find_all(["td"])
            
            if values[0].get_text(strip=True) in ["classType", "isValid", "objectType"]:
                continue

            vals = [values[i].get_text(strip=True) for i in range(num_headers)]
            extracted.append(",".join(vals))

        return extracted

    url = f"https://help.autodesk.com{ln}"

    rsp = requests.get(url)
    rsp.raise_for_status()

    soup = BeautifulSoup(rsp.text, "html.parser")

    name = get_name(soup)

    print(f"[EXTRACTING] {name} @ {ln}")

    description_h2 = soup.find("h2", class_="api", string=re.compile(r"^\s*Description\s*$"))
    description = get_content(description_h2)

    syntax = get_syntax(soup)

    property_h2 = soup.find("h2", class_="api", string=re.compile(r"^\s*Property Value\s*$"))
    
    property = "N/A"
    if property_h2:
        property = get_content(property_h2)

    parameters_h2 = soup.find("h2", class_="api", string=re.compile(r"^\s*Parameters\s*$"))

    parameters = []
    if parameters_h2:
        parameters = get_table(parameters_h2, 3)

    return_vals_h2 = soup.find("h2", class_="api", string=re.compile(r"^\s*Return Value(s?)\s*$"))

    return_vals = []
    if return_vals_h2:
        return_vals = get_table(return_vals_h2, 2)

    pairs = {
        "name": name,
        "description": description,
        "property_type": property,
        "method_parameters": parameters,
        "method_return_values": return_vals,
        "example_usage": syntax
    }

    res = format_object_attr_embedding(pairs)
    object_attrs_arr.append(res)

start_object = ""
start_object_found = True

def get_objects(content):

    global start_object, start_object_found

    if "children" in content:

        ttl = content["ttl"]
        ln = content["ln"]

        start_object_found = start_object_found or ttl == start_object
        
        if start_object_found and ttl != "Objects" and "🧪" not in ttl:
            # get_object(ttl, ln)
            print(f'"{ttl}",')
            pass

        for child in content["children"]:
            get_objects(child)

    else:

        ln = content["ln"]
        ttl = content["ttl"]

        if start_object_found and ln != "" and ttl not in ["classType", "isValid", "objectType"]:
            # get_object_attr(ln)
            pass

if __name__ == "__main__":

    global samples_arr, objects_arr, object_attrs_arr
    
    samples_arr = []

    objects_arr = []
    object_attrs_arr = []

    try:

        # Hidden API 

        url = "https://help.autodesk.com/view/fusion360/ENU/data/toctree.json"

        # Returns sidebar elements and their nested children
        # Each (leaf) children has property ln which is a relative link to its docs

        rsp = requests.get(url)
        json_content = rsp.json()

        # Samples

        # samples = json_content["books"][20]["children"][4]
        
        # get_samples(samples)
        # add_embeddings(samples_arr, "samples")

        # Objects

        objects = json_content["books"][20]["children"][3]["children"][0]
        
        get_objects(objects)
        # add_embeddings(objects_arr, "objects")
        add_embeddings(object_attrs_arr, "object_attrs")

    # except Exception as error:

    #     print(error)

    except:

        # Samples
        # add_embeddings(samples_arr, "samples")

        # Objects
        # add_embeddings(objects_arr, "objects")
        add_embeddings(object_attrs_arr, "object_attrs")

