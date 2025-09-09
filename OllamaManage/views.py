from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import re
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image, ImageEnhance, ImageFilter
import torch

MODEL_NAME = 'microsoft/trocr-base-handwritten'

processor = TrOCRProcessor.from_pretrained(MODEL_NAME)
model = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME)

def preprocess_image(image_file):
    image = Image.open(image_file)
    image = image.convert('RGB')
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
    pixel_values = processor(images=image, return_tensors="pt").pixel_values

    with torch.no_grad():
        generated_ids = model.generate(pixel_values)

    text = processor.decode(generated_ids[0], skip_special_tokens=True)
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
            return client.chat(model="llama3.2:3b", messages=[{'role': 'user', 'content': user_prompt}])

        try:
            response = chat_once()
        except Exception as e:
            msg = str(e).lower()
            if 'not found' in msg or '404' in msg:
                client.pull("llama3.2:3b")
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
