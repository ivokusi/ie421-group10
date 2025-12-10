from bs4 import BeautifulSoup, NavigableString, Tag
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

# Embeddings

def get_embeddings(texts):

    response = openai.embeddings.create(
        model="text-embedding-3-small",  # 1536 dims
        input=texts
    )

    embeddings = [d.embedding for d in response.data]
    return embeddings

def add_object_embeddings(arr, namespace):

    num_batches = math.ceil(len(arr) / 100)
    for i in range(0, len(arr), 100):

        print(f"[Processing] batch {(i // 100) + 1}/{num_batches}")
        
        batch = arr[i:i+100]
        texts = [text for (text, _, _) in batch]

        embeddings = get_embeddings(texts)

        vectors = [{ "id": id, "values": embedding, "metadata": metadata } for (_, metadata, id), embedding in zip(batch, embeddings)]

        index.upsert(
            vectors=vectors,
            namespace=namespace
        )

# Object

def format_object_embedding(pairs):

    class_name = pairs["class_name"]
    description = pairs["description"]

    text = f"""
    className: {class_name}
    description: {description}
    """

    metadata = {
        "className": class_name,
        "text": text
    }

    id = class_name

    return text, metadata, id

def get_object(suffix):

    global objects_arr

    def get_description(soup):

        description_h2 = soup.find("h2", class_="api", string=re.compile(r"\s*Description\s*"))

        description_parts = []
        for el in description_h2.next_elements:

            if isinstance(el, Tag) and el.name == "h2" and "api" in (el.get("class") or []):
                break

            if isinstance(el, NavigableString):
                
                text = el.strip()
                
                if text:
                    description_parts.append(text)

        description = " ".join(description_parts)
        return description
        
    url = f"https://help.autodesk.com{suffix}"

    rsp = requests.get(url)
    rsp.raise_for_status()

    soup = BeautifulSoup(rsp.text, "html.parser")

    object = soup.find("meta", attrs={"name": "contextid"})
    class_name = object.get("content")

    print(f"[Extarcting] {class_name}")

    description = get_description(soup)

    pairs = {
        "class_name": class_name,
        "description": description
    }
    
    res = format_object_embedding(pairs)
    objects_arr.append(res)

# Object Attrs (methods and properties)

def format_object_attr_embedding(attr_type, pairs):

    if attr_type == "Property":

        class_name = pairs["class_name"]
        property_name = pairs["property_name"]
        property_type = pairs["property_type"]
        property_description = pairs["property_description"]
        example_usage = pairs["example_usage"]

        text = f"""
        className: {class_name}
        propertyName: {property_name}
        propertyType: {property_type}
        propertyDescription: {property_description}
        exampleUsage: {example_usage}
        """

        metadata = {
            "className": class_name,
            "propertyName": property_name,
            "propertyType": property_type,
            "text": text
        }

        id = f"{class_name}.{property_name}"
        
    elif attr_type == "Method":

        class_name = pairs["class_name"]
        method_name = pairs["method_name"]
        method_description = pairs["method_description"]
        example_usage = pairs["example_usage"]
        methods_params = pairs.get("method_params", [])
        return_vals = pairs.get("return_vals", [])

        methodParams = f"methodParams[{len(methods_params)}]{{name,type,description}}\n\t{"\n\t".join(methods_params)}" if methods_params else "methodParams: None"
        returnVals = f"returnVals[{len(return_vals)}]{{type,description}}\n\t{"\n\t".join(return_vals)}" if return_vals else "returnVals: None"

        text = f"""
        className: {class_name}
        methodName: {method_name}
        {methodParams}
        {returnVals}
        methodDescription: {method_description}
        exampleUsage: {example_usage}
        """

        metadata = {
            "className": class_name,
            "methodName": method_name,
            "text": text
        }

        id = f"{class_name}.{method_name}"

    elif attr_type == "Event":

        class_name = pairs["class_name"]
        event_name = pairs["event_name"]
        event_description = pairs["event_description"]
        example_usage = pairs["example_usage"]

        text = f"""
        className: {class_name}
        eventName: {event_name}
        eventDescription: {event_description}
        exampleUsage: {example_usage}
        """

        metadata = {
            "className": class_name,
            "eventName": event_name,
            "text": text
        }

        id = f"{class_name}.{event_name}"

    return text, metadata, id

def get_object_attr(suffix):

    global object_attrs_arr

    def get_class_name_and_attr(soup):

        title = soup.select_one("title").text
        class_name, attr = title.split(".")

        attr_name, attr_type = attr.split(" ")

        return (class_name, attr_name, attr_type)

    def get_description(soup):

        description_h2 = soup.find("h2", class_="api", string=re.compile(r"\s*Description\s*"))

        description_parts = []
        for el in description_h2.next_elements:

            if isinstance(el, Tag) and el.name == "h2" and "api" in (el.get("class") or []):
                break

            if isinstance(el, NavigableString):
                
                text = el.strip()
                
                if text:
                    description_parts.append(text)

        description = " ".join(description_parts)
        return description

    def get_code(soup):

        python_div = soup.select_one("div#Python td")

        parts = []
        for node in python_div.descendants:
            
            if isinstance(node, Tag) and node.name == "br":
                parts.append("\n")
            
            elif isinstance(node, NavigableString):
                
                text = str(node)
                
                if text.strip():
                    parts.append(text)

        content = "".join(parts).strip()

        formatted_code_text = f"Python\n{content.strip()}"

        return formatted_code_text.strip()

    def get_property_type(soup):

        property_h2 = soup.find("h2", class_="api", string=re.compile(r"\s*Property Value\s*"))

        property_type = None
        if property_h2 is not None:
            for el in property_h2.next_elements:
                
                if isinstance(el, NavigableString):
                    
                    text = el.strip()
                    
                    text = "This is a read only property whose value is an Event."
                    match = re.match(r"This is a (read|read only|write|read/write) property whose value is (a|an) (.+)\.", text)
                    
                    if match:
                        property_type = match.groups()[2]  
                        break

        return property_type

    def get_table_vals(h2):

        vals = [] 
        if h2 is not None:
            
            params_table = h2.find_next("table")
            trs = params_table.find_all("tr")
            
            for row in trs[1:]: # ignore header
                val = [c.get_text(strip=True) for c in row.find_all(["td"])]
                vals.append(",".join(val))

        return vals

    url = f"https://help.autodesk.com{suffix}"

    rsp = requests.get(url)
    rsp.raise_for_status()

    soup = BeautifulSoup(rsp.text, "html.parser")

    class_name, attr_name, attr_type = get_class_name_and_attr(soup)
    description = get_description(soup)
    code = get_code(soup)
    property_type = get_property_type(soup)

    print(f"[Extarcting] {class_name}.{attr_name}")
    
    parameters_h2 = soup.find("h2", class_="api", string=re.compile(r"\s*Parameters\s*"))
    method_params = get_table_vals(parameters_h2) # name,type,description

    rets_h2 = soup.find("h2", class_="api", string=re.compile(r"\s*Return Value\s*"))
    return_vals = get_table_vals(rets_h2) # type,description

    if attr_type == "Property":
        
        pairs = {
            "class_name": class_name,
            "property_name": attr_name,
            "property_type": property_type,
            "property_description": description,
            "example_usage": code,
        }

    elif attr_type == "Method":

        pairs = {
            "class_name": class_name,
            "method_name": attr_name,
            "method_description": description,
            "example_usage": code,
            "method_params": method_params,
            "return_vals": return_vals
        }

    elif attr_type == "Event":

        pairs = {
            "class_name": class_name,
            "event_name": attr_name,
            "event_description": description,
            "example_usage": code,
        }

    else:

        raise Exception(f"Invalid for {class_name}")
    
    res = format_object_attr_embedding(attr_type, pairs)
    object_attrs_arr.append(res)

# Global methods

last_object_found = False
last_object = "SketchControlPointSpline"

def get_objects(content):

    global last_object_found, last_object

    if "children" in content:
        
        suffix = content["ln"]
        ttl = content["ttl"]

        if "🧪" in ttl:
            return

        last_object_found = last_object_found or ttl == last_object

        if suffix != "" and last_object_found:
            get_object(suffix)
        
        for child in content["children"]:
            get_objects(child)
    
    else:

        suffix = content["ln"]
        ttl = content["ttl"]

        if "🧪" in ttl:
            return

        if last_object_found and suffix != "" and ttl not in ["classType", "isValid", "objectType"]:
            get_object_attr(suffix)
        
if __name__ == "__main__":


    # Hidden API 

    try:

        url = "https://help.autodesk.com/view/fusion360/ENU/data/toctree.json"

        # Returns sidebar elements and their nested children
        # Each (leaf) children has property ln which is a relative link to its docs

        rsp = requests.get(url)
        json_content = rsp.json()

        objects = json_content["books"][20]["children"][3]["children"][0]

        get_objects(objects)
        add_object_embeddings(objects_arr, "objects")
        add_object_embeddings(object_attrs_arr, "object_attrs")

        # enums = json_content["books"][20]["children"][3]["children"][1]
        # samples = json_content["books"][20]["children"][4]

    except KeyboardInterrupt:
        
        add_object_embeddings(objects_arr, "objects")
        add_object_embeddings(object_attrs_arr, "object_attrs")

    except Exception as e:
        
        print(e)
        add_object_embeddings(objects_arr, "objects")
        add_object_embeddings(object_attrs_arr, "object_attrs")
    