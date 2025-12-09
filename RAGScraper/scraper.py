from bs4 import BeautifulSoup
import requests

def get_leafs(content, leafs):

    if "children" in content:

        for child in content["children"]:
            
            leafs = get_leafs(child, leafs)

    else:
        
        leafs.append((content["ttl"], content["ln"]))

    return leafs

if __name__ == "__main__":

    # Hidden API 

    url = "https://help.autodesk.com/view/fusion360/ENU/data/toctree.json"

    # Returns sidebar elements and their nested children
    # Each (leaf) children has property ln which is a relative link to its docs

    rsp = requests.get(url)

    json_content = rsp.json()
    leafs = format(json_content["books"][20])

    print(leafs)

    # url = "https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/MaterialSample_Sample.htm"
    
    # rsp = requests.get(url)
    # rsp.raise_for_status()

    # soup = BeautifulSoup(rsp.text, "html.parser")

    # print(soup.title)
    # print(soup.title.get_text())
