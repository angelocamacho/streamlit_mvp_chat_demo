import streamlit as st
import urllib.request
import json
import os
import ssl

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

allowSelfSignedHttps(True) # this line is needed if you use self-signed certificate in your scoring service.

st.title('Discovery Bot Chat Demo')

welcome_msg = "Hello 👋 I am a Discovery Bank chatbot that is able to assist you with queries regarding Discovery Bank."

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": welcome_msg}]

new_chat_context = False
if len(st.session_state.messages) == 1:
    new_chat_context = True
    
# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
# React to user input
if prompt := st.chat_input("How can I assist?"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # result = query_rag_pipeline(st.session_state.messages,new_context = new_chat_context)
    # print(result)
    print(st.session_state.messages)
    result = {
        'response': 'hello'
        
    }
    response = result['response']
    # sources = result['sources']
    # source_message = F"Here are my sources {sources[0]['file']} \n {sources[0]['score']}. \n\n\n  {sources[1]['file']} \n {sources[1]['score']}."
    # response = f"Echo: {prompt}"
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(response)
        # st.markdown(source_message)
    # # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
    # st.session_state.messages.append({"role": "assistant", "content": source_message})
