from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

import base64
import ollama
import json
import sys
@csrf_exempt
def chat_view(image_path, extraction_instructions):
    client = ollama.Client()
    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()
        encoded_image = base64.b64encode(image_data).decode('utf-8')
    
    message = {
        'role': 'user',
        'content': f'Extract the following data from the image: {extraction_instructions}. Return the result as valid JSON. Do not include any additional text or explanations.',
        'images': [encoded_image]
    }
    
    response = client.chat(model='llama3.2-vision', messages=[message])
    return render(request, 'chat.html')