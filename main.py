from typing import Union

from fastapi import FastAPI,Request,HTTPException

from pydantic import BaseModel
import json
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
from urllib.request import urlopen
from datetime import datetime
import pandas as pd
import re
from urllib.parse import urlencode
import base64

import os
import requests  

import numpy as np

import json

import asyncio

loop = asyncio.get_event_loop()



import httpx
import os
from typing import Dict, Any

from itertools import islice

class Item(BaseModel):
    docs: list = [],
    query: str

class TaskModel(BaseModel):
    task: str


app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"],  allow_methods=["GET", "POST", "PUT", "DELETE","OPTIONS"],  # Allow specific methods
    allow_headers=["*"]) # Allow GET requests from all origins

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/read/")
def read_output(path: str):

    print(path)
    try:
        with open(path.strip("/")) as f:
            content = f.read()
            return content
    except Exception as e:
        print(str(e))
        return HTTPException(status_code=404, detail="unable to read or file not found")



def llm_function(update_new_user_message):

    #update_new_user_message = task_description + "return only the output and no markdown " + file_contents 
    #print(update_new_user_message)

    #llm_token = os.environ['LLM_TOKEN']
    llm_token = os.environ['AIPROXY_TOKEN']
    output_response = requests.post(
    "https://llmfoundry.straive.com/openai/v1/chat/completions",
    headers={"Authorization": f"Bearer {llm_token}:my-test-project"},
    json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": update_new_user_message}]}
    )

    output_response_content = output_response.json()

    #print("the output response is")

    output_details = output_response_content['choices'][0]['message']['content']

    return output_details


def api_request(apiurl):

    response = requests.get(apiurl, verify=False)
    output_details = ''

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON data
        output_details = response.json()

    return output_details

@app.post('/run')

def task_run(item: TaskModel):
    
    #print(item.task)

    image_extension = [".jpg",".png"]
    file_extension = [".txt",".log"]
    llm_token = os.environ['AIPROXY_TOKEN']

    #rint(llm_token)
    user_message_query = "write the task description,main task,input and output file give only json format with out markdown" + item.task
    response = requests.post(
    "https://llmfoundry.straive.com/openai/v1/chat/completions",
    headers={"Authorization": f"Bearer {llm_token}:my-test-project"},
    json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": user_message_query}]}
    )

    response_content = response.json()

    #print(response_content)

    task_details = response_content['choices'][0]['message']['content']
    
    task_json_format = json.loads(task_details)

    #print(task_json_format['task_description'])
    #print(task_json_format['input_file'])
    #print(task_json_format['output_file'])

    task_description = task_json_format['task_description']
    input_file = task_json_format['input_file']
    output_file = task_json_format['output_file']

    if 'name' in output_file:
        output_file = output_file['name']
    else:
        output_file = output_file

    #print(input_file)

    input_type = type(input_file).__name__

    if 'url' in input_file:
        #print("the input file url is "+ input_file['url'])
        output_details = api_request(input_file['url'])

    elif input_type == "dict":
        output_details = output_file

    else:
        check_file = os.path.isabs(input_file)

        #print(check_file)
        if check_file == True:
            input_file = input_file
        else:
            input_file = "/data/" + os.path.basename(input_file)

        #print(input_file)

        try: 
            
            input_extension = os.path.splitext(input_file)[1]
            #print("input_extension" + input_extension)

            if input_extension in image_extension:

                #print(input_extension)
                #print(input_file)

                with open(input_file.strip("/"),"rb") as image_file:
                    #print("coming after file open")
                    file_contents = base64.b64encode(image_file.read())
                    
                    #print(file_contents)

                    update_new_user_message =  [{
                    "type": "image_url",
                    "image_url": {
                        "url": "data:image/png;base64,"+ file_contents.decode("utf-8"),
                        "detail": "low"
                    }
                    },
                    {
                    "type": "text",
                    "text": task_description + "return only the output and no markdown "
                    }]
                    

            elif input_extension in file_extension:

                with open(input_file) as user_file:
                    file_contents = user_file.read()
                    update_new_user_message = task_description + "return only the output and no markdown " + file_contents

            else:
                    with open(input_file) as user_file:
                        file_contents = user_file.read()
                        update_new_user_message = task_description + "return only the output and no markdown " + file_contents
            output_details = llm_function(update_new_user_message)

        except Exception as e:
            #print(str(e))
            return "error in reading input file"

    #returns JSON object as a dictionary
    
    #print(file_contents)
    if input_type == "dict":
        output_format = output_details

    else:

        try:
            output_extension = os.path.splitext(output_file)[1]
            
        except Exception as e:
            return "error in outfile"


        #print(output_details)
        if output_extension == ".json":
            output_type = type(output_details).__name__
            if(output_type == "dict"):
                output_format = output_details
            else:
                output_format = json.loads(output_details)
            
        
        else:
            output_format = output_details
   

    #print(output_format)
    #print(output_file)

    # Write data to a JSON file
    try:

        if input_type == "dict":
            return output_format
        else:
            
            with open(output_file.strip("/"), 'w+') as f:
            #with open('data/credit_card.txt', 'w+') as f:
                if output_extension == ".json":
                    json.dump(output_format, f, indent=4)
                
                else:
                    f.write(output_format)
                    
            return "success"  
            
    except Exception as e:
        #print(str(e))
        return HTTPException(status_code=500, detail="error")



    

    



    

