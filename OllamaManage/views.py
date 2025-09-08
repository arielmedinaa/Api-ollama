from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import base64
import json
import re
import ollama

MODEL_NAME = 'llama3.2-vision:11b'

@csrf_exempt
def analyze_image(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Solo se permite el método POST'}, status=405)

    if 'image' not in request.FILES:
        return JsonResponse({'error': 'Falta el archivo de imagen en el campo "image"'}, status=400)

    try:
        image_file = request.FILES['image']
        image_bytes = image_file.read()
        encoded_image = base64.b64encode(image_bytes).decode('utf-8')

        user_prompt = request.POST.get(
            'prompt',
            'Devuelve únicamente un JSON válido con tu análisis del contenido de la imagen, sin texto adicional.'
        )

        messages = [
            {
                'role': 'user',
                'content': f"{user_prompt}",
                'images': [encoded_image],
            }
        ]

        client = ollama.Client()

        def chat_once():
            return client.chat(model=MODEL_NAME, messages=messages)

        try:
            response = chat_once()
        except Exception as e:
            msg = str(e).lower()
            if 'not found' in msg or '404' in msg:
                # Si el modelo no existe en el servidor, intenta descargarlo y reintenta una vez
                client.pull(MODEL_NAME)
                response = chat_once()
            else:
                raise

        content = response.get('message', {}).get('content', '') if isinstance(response, dict) else str(response)
        content = content.strip()

        if content.startswith('```'):
            match = re.search(r"```(?:json)?\s*(.*?)```", content, re.S)
            if match:
                content = match.group(1).strip()
        try:
            data = json.loads(content)
            return JsonResponse(data, safe=False)
        except Exception:
            return JsonResponse({'result': content})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)