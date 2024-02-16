import streamlit as st
import urllib.request
import json
import os
import ssl

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import cv2
from screeninfo import get_monitors
import imutils

from azure.storage.blob import ContainerClient

def allowSelfSignedHttps(allowed):
    # bypass the server certificate verification on client side
    if allowed and not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None):
        ssl._create_default_https_context = ssl._create_unverified_context

def query_rag_pipeline(query,session_messages,new_context = False):
    data = {
        "query": query,
        "conv_history": session_messages,
        "new_context": new_context
    }

    body = str.encode(json.dumps(data))

    url = os.environ['AZURE_URL']
    # Replace this with the primary/secondary key or AMLToken for the endpoint
    api_key = os.environ['AZURE_API_KEY']
    if not api_key:
        raise Exception("A key should be provided to invoke the endpoint")

    # The azureml-model-deployment header will force the request to go to a specific deployment.
    # Remove this header to have the request observe the endpoint traffic rules
    headers = {'Content-Type':'application/json', 'Authorization':('Bearer '+ api_key), 'azureml-model-deployment': 'zephyr-7b-beta-1' }

    req = urllib.request.Request(url, body, headers)

    try:
        response = urllib.request.urlopen(req)

        result = response.read()
        jsonResponse = json.loads(result.decode())
        # print(result)
    except urllib.error.HTTPError as error:
        print("The request failed with status code: " + str(error.code))

        # Print the headers - they include the requert ID and the timestamp, which are useful for debugging the failure
        print(error.info())
        print(error.read().decode("utf8", 'ignore'))
    
    return jsonResponse

def get_screen_resolution():

    global width
    global height
    for m in get_monitors():
        if m.is_primary:
            width = m.width
            height = m.height
            

def setup():
    
    allowSelfSignedHttps(True) # this line is needed if you use self-signed certificate in your scoring service.
    if "container_client" not in st.session_state:
        container_client = ContainerClient(os.environ['AZURE_BLOB_ACCOUNT_URL'],os.environ['AZURE_BLOB_JPG_CONTAINER'],os.environ['AZURE_BLOB_KEY'])
        st.session_state.container_client = container_client
    
    
    get_screen_resolution()
    
    st.title('Discovery Bot Chat Demo')
    welcome_msg = "Hello 👋 I am a Discovery Bank chatbot that is able to assist you with queries regarding Discovery Bank."
    with st.chat_message("assistant"):
        st.markdown(welcome_msg)
        
    
    # messages are the messages the user sees, we keep track of everything
    # chat_context is only the chat history we want to pass back
    # setup session state memory
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.chat_context = []
        
    global new_chat_context
    new_chat_context = False
    if len(st.session_state.messages) == 0:
        new_chat_context = True
        
    else: 
        # Display chat messages from history on app rerun
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "has_button" in message and message["has_button"]:
                    create_button(message["btn_key"],message["source_file"])
                
                
def show_user_source(file_path):

    if "image_open" not in st.session_state:
        st.session_state.image_open = True
    elif st.session_state.image_open:
        cv2.destroyAllWindows() 
    
    file_path_parts =  file_path.split("\\")
    azure_file_path = file_path_parts[1] +'/' + file_path_parts[2]
    print(azure_file_path)
    try:
        blob_name = st.session_state.container_client.list_blobs(name_starts_with=azure_file_path).next()
    except:
        print(f"No blob found with the file_path {azure_file_path}")
        return
    
    download_stream = st.session_state.container_client.download_blob(blob_name)
    blob_bytes = download_stream.readall()
    
    with open(file_path_parts[2], "wb") as file:
        file.write(blob_bytes)
        
    image = cv2.imread(file_path_parts[2]) 
    image = imutils.resize(image,width = 700)
    # image = image_resize(image, height = 800)

    window_name = 'Document source'
  
    # Using cv2.imshow() method 
    # Displaying the imag
    cv2.imshow(window_name, image) 
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
    # cv2.resizeWindow(window_name, int(0.4* width), int(0.8* height))
    # cv2.resizeWindow(window_name, 600, 600)
    
    # waits for user to press any key 
    # (this is necessary to avoid Python kernel form crashing) 
    
    st.session_state.image_open = True
    cv2.waitKey(0) 
    
    # closing all open windows 
    cv2.destroyAllWindows() 
    st.session_state.image_open = False
    
def create_button(btn_key,source_file):
    st.button(key = btn_key,label = "View Source", on_click = show_user_source,kwargs = {"file_path":source_file})

def react_to_message():
                
    # React to user input
    # if prompt := st.chat_input("How can I assist?"):
    #     with st.chat_message("assistant"):
    #         st.markdown("Thanks")
            
    #         for i in range(4):
    #             st.markdown(i)
    #             create_button(i,"target-dir\discovery-card-miles-terms-and-conditions_parts\discovery-card-miles-terms-and-conditions_part_7.jpg")
                # st.button(key = i,label = "View Source", on_click = show_user_source,kwargs = {"file_path": "target-dir\discovery-card-miles-terms-and-conditions_parts\discovery-card-miles-terms-and-conditions_part_7.jpg"})
    if prompt := st.chat_input("How can I assist?"):
        
        # Display user message in chat message container
        st.chat_message("user").markdown(prompt)
        
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.chat_context.append({"role": "user", "content": prompt})
        

        result = query_rag_pipeline(prompt,st.session_state.chat_context,new_context = new_chat_context)
        # print(result)
        response = result['response']
        sources = result['sources']
        # source_message = response + '\n'

        
        with st.chat_message("assistant"):
            st.markdown(response)
            st.session_state.chat_context.append({"role": "assistant", "content": response})
            st.session_state.messages.append({"role": "assistant", "content": response})


            for source in sources:
                print(float(source['score']))
                # if float(source['score']) > 0.1:
                
                source_message = F"- Source: {source['file']} \n {source['score']} \n {source['text'].encode('ascii', errors='ignore')}\n\n\n"
                st.markdown(source_message)
                
                
                # source_message = source_message + F"- Source: {source['file']} \n {source['score']} \n {source['text'].encode('ascii', errors='ignore')}\n\n\n" 
                if 'faq' not in source['file']:
                    create_button(source['text'].encode('ascii', errors='ignore'),source['file'])
                    st.session_state.messages.append({"role": "assistant", "content": source_message, "has_button": True, "btn_key": source['text'].encode('ascii', errors='ignore'), "source_file": source['file']})
                else:
                    st.session_state.messages.append({"role": "assistant", "content": source_message, "has_button": False})
                    
                        # st.button(,label = "View Source", on_click = show_user_source,kwargs = {"file_path":})
                
            # st.markdown(source_message)

            
        # complete_message = F"{response} + \n\n + {source_message}"
        # # response = f"Echo: {prompt}"
        # # Display assistant response in chat message container
        # with st.chat_message("assistant"):
        #     st.markdown(complete_message)
        
        
        # Add assistant response to chat history

setup()
react_to_message()
# show_user_source("target-dir\discovery-card-miles-terms-and-conditions_parts\discovery-card-miles-terms-and-conditions_part_7.jpg")
# react_to_message()
