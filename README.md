# AI Creative Partner Pipeline

## Overview

The AI Creative Partner Pipeline is an application designed to automate a creative workflow. It takes a user's textual prompt, enhances it (simulating an LLM), then uses this enhanced prompt to generate an image via a Text-to-Image Openfabric application. Subsequently, the generated image is used as input for an Image-to-3D model Openfabric application to produce a 3D model. The pipeline also incorporates short-term and long-term memory functionalities, logging session details and saving generated assets and session metadata to the filesystem.

## Features

*   **Prompt Enhancement:** Simulates an LLM to enhance user prompts for better generation results (e.g., adding keywords like "detailed, vibrant, 4k").
*   **Text-to-Image Generation:** Integrates with an Openfabric Text-to-Image application to generate images from text prompts.
*   **Image-to-3D Model Generation:** Integrates with an Openfabric Image-to-3D application to create 3D models from input images.
*   **Short-Term Memory:** Logs the context of each execution session, including original and enhanced prompts, and paths to generated assets.
*   **Long-Term Memory:**
    *   Saves generated images and 3D models to a structured directory (`generated_assets/`) with unique, timestamped filenames.
    *   Saves detailed session metadata (prompts, asset paths) as JSON files in a `memory_store/` directory, also with timestamped filenames, allowing for future recall and analysis.

## Setup and Configuration

### Prerequisites

*   **Python:** Python 3.9+ is recommended.
*   **Openfabric SDK:** The application is built using the Openfabric Python SDK.
*   **Poetry:** For dependency management (optional, if you prefer manual setup).

### Dependencies

Dependencies are managed via `pyproject.toml`. If you have Poetry installed, you can install dependencies using:
```bash
poetry install
```
Alternatively, a `requirements.txt` might be provided or can be generated from `poetry.lock`.

### Configuration: `config/execution.json`

The `config/execution.json` file is crucial for defining the Openfabric applications that this pipeline will call. It maps a user (e.g., "super-user") to a list of application IDs.

**Example `config/execution.json` structure:**

```json
{
  "super-user": {
    "app_ids": [
      "f0997a01-d6d3-a5fe-53d8-561300318557", // Text-to-Image App ID
      "69543f29-4d41-4afc-7f29-3d51591f11eb"  // Image-to-3D App ID
    ]
  }
  // Other configuration entries for input/output schemas, etc.
}
```

**Important:** The `app_ids` listed must be correct and accessible to your Openfabric environment for the pipeline to function as expected. Ensure these IDs correspond to the deployed Text-to-Image and Image-to-3D applications you intend to use.

## How to Run

### Locally with `start.sh`

The primary way to run the application locally is using the provided shell script:

```bash
./start.sh
```

This script typically handles setting up the environment and starting the Openfabric application.

### Docker

A `Dockerfile` is provided, allowing you to build and run the application in a containerized environment.
Build the image:
```bash
docker build -t ai-creative-pipeline .
```
Run the container (example, actual port may vary):
```bash
docker run -p 8888:8080 ai-creative-pipeline
```

### Accessing the Application

Once running, the application's API can typically be accessed via a Swagger UI at:
`http://localhost:8888/swagger-ui/#/App/post_execution` (The port `8888` is an example and might differ based on your `start.sh` or Docker configuration).

## Pipeline Workflow

1.  **User Prompt:** The user submits a text prompt (e.g., "a futuristic robot").
2.  **LLM Enhancement (Simulated):** The input prompt is enhanced with additional descriptive keywords (e.g., ", detailed, vibrant, 4k, cinematic lighting").
3.  **Text-to-Image App Call:** The enhanced prompt is sent to the configured Text-to-Image Openfabric application.
4.  **Image Output:** The Text-to-Image app returns image data. This image is saved locally.
5.  **Image-to-3D App Call:** The generated image data is sent to the configured Image-to-3D Openfabric application.
6.  **3D Model Output:** The Image-to-3D app returns 3D model data (e.g., in GLB format). This model is saved locally.

## Memory Functionality

### Short-Term Memory

During each execution of the pipeline, key information about the session is collected and logged. This includes:
*   The original prompt from the user.
*   The enhanced prompt after simulated LLM processing.
*   The file path of the generated image (if successful).
*   The file path of the generated 3D model (if successful).

This information is logged to the console, providing a real-time trace of the session's activities.

### Long-Term Memory

To persist data beyond a single session and allow for later analysis or asset reuse, the pipeline implements long-term memory:

*   **Asset Storage:** Generated images and 3D models are saved with unique, timestamped filenames in the `generated_assets/` directory.
    *   Example: `generated_assets/image_20231027_103045_123456.png`
    *   Example: `generated_assets/model_20231027_103100_654321.glb`

*   **Session Metadata Storage:** A JSON file summarizing the session is saved in the `memory_store/` directory, also with a timestamped filename. This file includes the prompts, paths to the saved assets, and any other relevant session data.
    *   Example: `memory_store/session_20231027_103100_654321.json`

This persistent storage ensures that creative assets and their associated context are not lost and can be cataloged or used in further workflows (though automatic recall/reuse mechanisms are not part of the current implementation).

## Example Usage

### Input

Send a POST request to the execution endpoint (e.g., `/execution`) with a JSON body like:

```json
{
  "prompt": "A majestic space whale"
}
```

### Expected Output

1.  **API Response (JSON):**
    ```json
    {
      "message": "Image generated for prompt: 'A majestic space whale'. Saved as generated_assets/image_TIMESTAMP.png. 3D model generated and saved as generated_assets/model_TIMESTAMP.glb.",
      "image_path": "generated_assets/image_TIMESTAMP.png",
      "model_path": "generated_assets/model_TIMESTAMP.glb"
    }
    ```
    *(Note: `TIMESTAMP` will be actual timestamp values)*

2.  **Files Created:**
    *   `generated_assets/image_TIMESTAMP.png` (actual image file)
    *   `generated_assets/model_TIMESTAMP.glb` (actual 3D model file)
    *   `memory_store/session_TIMESTAMP.json` (session metadata file)

3.  **Content of `memory_store/session_TIMESTAMP.json` (Example):**
    ```json
    {
        "original_prompt": "A majestic space whale",
        "enhanced_prompt": "A majestic space whale, detailed, vibrant, 4k, cinematic lighting",
        "generated_image_path": "generated_assets/image_20231027_110000_123456.png",
        "generated_model_path": "generated_assets/model_20231027_110005_654321.glb"
    }
    ```

## Project Structure

*   `main.py`: The main entry point of the application, contains the `execute` function orchestrating the pipeline.
*   `core/`: Contains core functionalities like the `Stub` for Openfabric app communication.
    *   `stub.py`: Handles calls to external Openfabric applications.
*   `config/`: Contains configuration files.
    *   `execution.json`: Defines app IDs and callback configurations.
    *   `manifest.json`: Standard Openfabric manifest file.
*   `ontology_dc8f06af066e4a7880a5938933236037/`: Contains the data classes (schemas) for input, output, and configuration, specific to this Openfabric app.
*   `generated_assets/`: Directory where generated images and 3D models are stored. (Created automatically)
*   `memory_store/`: Directory where session metadata JSON files are stored. (Created automatically)
*   `start.sh`: Script to run the application locally.
*   `Dockerfile`: For building and running the application in a Docker container.
*   `pyproject.toml` & `poetry.lock`: Dependency management files for Poetry.
*   `README.md`: This file - providing documentation for the project.

---
*This README provides a comprehensive guide to the AI Creative Partner Pipeline. Adjust paths, versions, and specific commands as per your local environment and project evolution.*
