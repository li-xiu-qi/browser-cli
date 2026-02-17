# `smolagents`

<div class="flex justify-center">
    <img src="https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/smolagents/license_to_call.png" style="max-width:700px"/>
</div>

## ¿Qué es smolagents?

`smolagents` es una biblioteca de código abierto en Python, diseñada para facilitar al máximo la construcción y ejecución de agentes con solo unas pocas líneas de código.

Algunos aspectos clave de `smolagents` incluyen:

 **Simplicidad**: La lógica de los agentes se implementa en aproximadamente unas mil líneas de código. ¡Lo hemos mantenido simple, sin agregar complejidad innecesaria!

‍ **Soporte avanzado para Agentes de Código**: [`CodeAgent`](reference/agents#smolagents.CodeAgent) ejecuta acciones directamente en código (en lugar de que los agentes generen código), lo que permite usar varias herramientas o realizar cálculos de manera flexible. Esto hace posible combinar de manera sencilla funciones anidadas, bucles, condicionales y mucho más. Para garantizar la seguridad, el agente puede [ejecutarse en un entorno aislado](tutorials/secure_code_execution) usando [E2B](https://e2b.dev/) o Docker.

 **Integración nativa con agentes de herramientas**: además de los CodeAgent,  [`ToolCallingAgent`](reference/agents#smolagents.ToolCallingAgent) es compatible con el esquema tradicional basado en JSON/texto para casos en los que se prefiera este formato.

 **Integraciones con el Hub**: mediante Gradio Spaces es posible compartir y cargar múltiples agentes junto con herramientas desde o hacia el Hub de manera sencilla.

 **Independencia respecto al modelo**: integra fácilmente grandes modelos de lenguaje (LLM) alojados en el Hub mediante los [proveedores de inferencia](https://huggingface.co/docs/inference-providers/index), APIs externas como OpenAI, Anthropic y muchos otros a través de la integración con LiteLLM. Además, es posible ejecutar localmente estos sistemas utilizando Transformers u Ollama. Es sencillo y flexible potenciar un agente con tu LLM preferido.

️ **Independencia respecto a la modalidad**: los agentes pueden procesar diferentes tipos de entrada (_inputs_) como texto, visión, video y audio, ampliando considerablemente el rango de aplicaciones posibles. Consulta este [tutorial](https://huggingface.co/docs/smolagents/v1.21.0/en/examples/web_browser) sobre el área de visión.

️ **Independencia respecto a las herramientas**: existe una gran variedad de herramientas en cualquier [Servidor MCP](reference/tools#smolagents.ToolCollection.from_mcp), marcos de orquestación como [LangChain](reference/tools#smolagents.Tool.from_langchain) e incluso existe la posibilidad de usar el [Hub Space](reference/tools#smolagents.Tool.from_space) como herramienta.

 **Herramientas de CLI**: incluye utilidades en línea de comandos (smolagent, webagent) para ejecutar agentes rápidamente sin código repetitivo.

## Inicio Rápido

[[open-in-colab]]

¡Comienza a usar smolagents en solo unos minutos! Esta guía te mostrará cómo crear y ejecutar tu primer agente.

### Instalación

Instala smolagents usando pip:

```bash
pip install smolagents[toolkit]  # Incluye herramientas básicas como búsqueda web.
```

### Crea tu Primer Agente

A continuación se detalla un ejemplo básico para crear y ejecutar un agente:


```python
from smolagents import CodeAgent, InferenceClientModel

# Iniciar el modelo (utilizando la API de Hugging Face Inference)
model = InferenceClientModel()  # Utiliza el modelo por defecto

# Crear un agente sin herramientas
agent = CodeAgent(tools=[], model=model)

# Ejecuta el agente con una tarea específica
result = agent.run("Calculate the sum of numbers from 1 to 10")
print(result)
```
¡Eso es todo! El agente usará Python para completar la tarea y entregar el resultado.

### Agregar Herramientas

Mejoremos las capacidades de nuestro agente añadiendo algunas herramientas:

```python
from smolagents import CodeAgent, InferenceClientModel, DuckDuckGoSearchTool

model = InferenceClientModel()
agent = CodeAgent(
    tools=[DuckDuckGoSearchTool()],
    model=model,
)

# ¡Ahora el agente puede buscar información en Internet!
result = agent.run("What is the current weather in Paris?")
print(result)
```

### Usar Modelos Diferentes

Puedes usar diferentes modelos con los agentes:

```python
# Usar un modelo específico de Hugging Face
model = InferenceClientModel(model_id="meta-llama/Llama-2-70b-chat-hf")

# Usar la API de OpenAI/Anthropic (requiere smolagents[litellm])
from smolagents import LiteLLMModel
model = LiteLLMModel(model_id="gpt-4")

# Utilizar modelos locales (requiere smolagents[transformers])
from smolagents import TransformersModel
model = TransformersModel(model_id="meta-llama/Llama-2-7b-chat-hf")
```

## Próximos Pasos

- Aprende a configurar smolagents con diferentes modelos y herramientas en la [Guía de Instalación](installation).
- Revisa el [Tutorial Guiado](guided_tour) y aprende a usar funciones más avanzadas.
- Aprende a construir [herramientas personalizadas](tutorials/tools).
- Conoce más sobre la [ejecución segura de código](tutorials/secure_code_execution).
- Explora el desarrollo de [sistemas multiagente](tutorials/building_good_agents).

<div class="mt-10">
  <div class="w-full flex flex-col space-y-4 md:space-y-0 md:grid md:grid-cols-2 md:gap-y-4 md:gap-x-5">
    <a class="!no-underline border dark:border-gray-700 p-5 rounded-lg shadow hover:shadow-lg" href="./guided_tour"
      ><div class="w-full text-center bg-gradient-to-br from-blue-400 to-blue-500 rounded-lg py-1.5 font-semibold mb-5 text-white text-lg leading-relaxed">Tutorial Guiado</div>
      <p class="text-gray-700">Domina los conceptos básicos y aprende a manejar agentes. Empieza aquí si nunca los has utilizado.</p>
    </a>
    <a class="!no-underline border dark:border-gray-700 p-5 rounded-lg shadow hover:shadow-lg" href="./examples/text_to_sql"
      ><div class="w-full text-center bg-gradient-to-br from-indigo-400 to-indigo-500 rounded-lg py-1.5 font-semibold mb-5 text-white text-lg leading-relaxed">Guías prácticas</div>
      <p class="text-gray-700">Ejemplos prácticos para guiarte en diferentes proyectos. ¡Desarrolla un agente que genere y valide consultas SQL!</p>
    </a>
    <a class="!no-underline border dark:border-gray-700 p-5 rounded-lg shadow hover:shadow-lg" href="./conceptual_guides/intro_agents"
      ><div class="w-full text-center bg-gradient-to-br from-pink-400 to-pink-500 rounded-lg py-1.5 font-semibold mb-5 text-white text-lg leading-relaxed">Guías Conceptuales</div>
      <p class="text-gray-700">Conceptos avanzados para profundizar en la comprensión de temas clave.</p>
   </a>
    <a class="!no-underline border dark:border-gray-700 p-5 rounded-lg shadow hover:shadow-lg" href="./tutorials/building_good_agents"
      ><div class="w-full text-center bg-gradient-to-br from-purple-400 to-purple-500 rounded-lg py-1.5 font-semibold mb-5 text-white text-lg leading-relaxed">Tutoriales</div>
      <p class="text-gray-700">Tutoriales completos que cubren aspectos clave para el desarrollo de agentes.</p>
    </a>
  </div>
</div>
