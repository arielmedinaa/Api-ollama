from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import re
import ollama
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter

MODEL_NAME = 'llama3.2:3b'

def preprocess_image(image_file):
    image = Image.open(image_file)
    image = image.convert('L')
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2)

    image = image.filter(ImageFilter.MedianFilter())
    base_width = 1800
    wpercent = (base_width / float(image.size[0]))
    hsize = int((float(image.size[1]) * float(wpercent)))
    image = image.resize((base_width, hsize), Image.LANCZOS)

    return image

def extract_text(image_file):
    image = preprocess_image(image_file)
    text = pytesseract.image_to_string(image, lang="spa", config="--psm 11")
    print(text)
    return text

@csrf_exempt
def analyze_image(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Solo se permite el método POST'}, status=405)

    if 'image' not in request.FILES:
        return JsonResponse({'error': 'Falta el archivo de imagen en el campo "image"'}, status=400)

    try:
        image_file = request.FILES['image']
        text = extract_text(image_file)

        user_prompt = request.POST.get(
            'prompt',
            f"""
Convierte este texto de factura en un JSON válido 

Texto:
{text}

Devuelve **solo JSON**, nada de texto adicional.
"""
        )

        client = ollama.Client()

        def chat_once():
            return client.chat(model=MODEL_NAME, messages=[{'role': 'user', 'content': user_prompt}])

        try:
            response = chat_once()
        except Exception as e:
            msg = str(e).lower()
            if 'not found' in msg or '404' in msg:
                client.pull(MODEL_NAME)
                response = chat_once()
            else:
                raise

        if isinstance(response, dict):
            content = response.get("message", {}).get("content", "")
        else:
            try:
                content = response.message.content
            except AttributeError:
                content = str(response)

        content = content.strip()
        if content.startswith('```'):
            match = re.search(r"```(?:json)?\s*(.*?)```", content, re.S)
            if match:
                content = match.group(1).strip()

        try:
            data = json.loads(content)
            return JsonResponse(data, safe=False)
        except Exception:
            print(f"Error parsing JSON from model output:\n{content}")
            return JsonResponse({'result': content})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
