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
from urlextract import URLExtract

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

def is_json(myjson):
  try:
    json.loads(myjson)
  except ValueError as e:
    return False
  return True

def is_json_empty(json_obj):
    # return true if length is 0.
    return len(json_obj) == 0

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

    print("user message")
    print(update_new_user_message)
    output_response = requests.post(
    #"https://llmfoundry.straive.com/openai/v1/chat/completions",
    "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions",
    headers={"Authorization": f"Bearer {llm_token}"},
    json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": update_new_user_message}]},verify=False)

    output_response_content = output_response.json()

    output_details = output_response_content['choices'][0]['message']['content']

    return output_details


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')



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
    file_extension = [".txt",".log",".json"]

    #user_message_query = "write the task description,input and output file name represent it in json keys and give response only in json format with out markdown:" + item.task
    
    # old_user_message_query = "write the task description,input and output file name represent it in json keys and give response only in json format with out markdown:" + item.task
    user_message_query = "write the exact task description,main task, input and output file name if present in the user message and represent it in json keys else don't give details and provide response only in json format with out markdown:" + item.task

    task_details = llm_function(user_message_query)
    
    task_json_format = json.loads(task_details)

    #print(task_json_format['task_description'])
    #print(task_json_format['input_file'])
    #print(task_json_format['output_file'])

    task_description = task_json_format['task_description']
    input_file = task_json_format['input_file']
    output_file = task_json_format['output_file']

    input_type = type(input_file).__name__

    #print(task_json_format)
    #print(input_type)

    if input_file is not None:
        check_file = os.path.isabs(input_file)

        #print(check_file)

        if check_file == True:

            input_format = "file"
            

            #print(check_file)
            if check_file == True:
                input_file = input_file
            else:
                input_file = "/data/" + os.path.basename(input_file)

            #print(input_file)

            try: 
                
                input_extension = os.path.splitext(input_file)[1]

                if input_extension in image_extension:
                    file_content = encode_image(input_file.strip("/"))
                    #print(file_content)

                    update_new_user_message =  [{
                    "type": "image_url",
                    "image_url": {
                        "url" : "data:image/png;base64," + file_content,
                        "detail": "low"
                        
                    }
                    },
                    {
                    "type": "text",
                    "text": task_json_format['main_task'] + "return only the output"
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
                return "error in reading task details"

        else:
            output_details = output_file
    else:
        #print("the input is null")

        secondary_message = "what are the input and output also example code block in the below message return response only in json format and no markdown:" + item.task
        secondary_output_details = llm_function(secondary_message)

        secondary_output_json = json.loads(secondary_output_details)

        check_input = secondary_output_json["input"]

        if 'url' in check_input:
            api_response_call = api_request(check_input['url'])
            check_json_status = is_json_empty(api_response_call)

            if check_json_status is not True:
                secondary_output_details = api_response_call

        
    try:

        if input_file is not None:
            output_format = output_details
        else:
            output_format = secondary_output_details

        #print("the output format is")
        #print(output_format)

        output_type = type(output_format).__name__
        

        if input_file is not None:
            if output_file is not None:
                output_extension = os.path.splitext(output_file)[1]
                
                with open(output_file.strip("/"), 'w+') as f:
                    if output_extension == ".json":

                        json_status = is_json(output_format)
                        if json_status == True:
                            f.write(output_format)
                        else:
                            json.dump(output_format, f, indent=4)
                    
                    else:
                        f.write(output_format)
                        
                            
            else:
                if (output_type == "dict"):
                    output_format = json.dumps(output_format,indent=4)
                else:
                    output_format = json.loads(output_format)
                return output_format
        else:

            if (output_type == "dict"):
                output_format = json.dumps(output_format,indent=4)
            else:
                output_format = json.loads(output_format)
            return output_format
            
        return "success" 

    except Exception as e:
        #print(str(e))
        return HTTPException(status_code=500, detail="error")
