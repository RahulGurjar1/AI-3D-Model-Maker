import logging
import os
import base64
import json
from datetime import datetime
from typing import Dict

from ontology_dc8f06af066e4a7880a5938933236037.config import ConfigClass
from ontology_dc8f06af066e4a7880a5938933236037.input import InputClass
from ontology_dc8f06af066e4a7880a5938933236037.output import OutputClass
from openfabric_pysdk.context import AppModel, State
from core.stub import Stub

# Configurations for the app
configurations: Dict[str, ConfigClass] = dict()

############################################################
# Config callback function
############################################################
def config(configuration: Dict[str, ConfigClass], state: State) -> None:
    """
    Stores user-specific configuration data.

    Args:
        configuration (Dict[str, ConfigClass]): A mapping of user IDs to configuration objects.
        state (State): The current state of the application (not used in this implementation).
    """
    for uid, conf in configuration.items():
        logging.info(f"Saving new config for user with id:'{uid}'")
        configurations[uid] = conf


############################################################
# Execution callback function
############################################################
def execute(model: AppModel) -> None:
    """
    Main execution entry point for handling a model pass.

    Args:
        model (AppModel): The model object containing request and response structures.
    """

    # Retrieve input
    request: InputClass = model.request
    response: OutputClass = model.response  # Get response object early

    # Create directories for generated assets and memory store
    os.makedirs("generated_assets", exist_ok=True)
    os.makedirs("memory_store", exist_ok=True)

    # Initialize session data for short-term memory
    session_data = {}
    session_data['original_prompt'] = request.prompt

    # Initialize response paths
    response.image_path = None
    response.model_path = None

    # Retrieve user config
    user_config: ConfigClass = configurations.get('super-user', None)
    logging.info(f"{configurations}")

    # Initialize the Stub with app IDs
    app_ids = user_config.app_ids if user_config else []
    logging.info(f"Initializing Stub with app_ids: {app_ids}")
    stub = Stub(app_ids)

    # Define App IDs from configuration
    text_to_image_app_id = None
    image_to_3d_app_id = None

    if len(app_ids) >= 2:
        text_to_image_app_id = app_ids[0]
        image_to_3d_app_id = app_ids[1]
        logging.info(f"Text-to-Image App ID: {text_to_image_app_id}")
        logging.info(f"Image-to-3D App ID: {image_to_3d_app_id}")
    else:
        logging.error("Not enough app_ids configured. Expected at least 2 for Text-to-Image and Image-to-3D.")
        # Further error handling or early return could be implemented here.
        # For now, calls will fail if IDs are None, and this will be logged by conditional checks below.

    # ------------------------------
    # TODO : add your magic here
    # ------------------------------

    # Enhance prompt
    enhanced_prompt = enhance_prompt_with_llm(request.prompt)
    session_data['enhanced_prompt'] = enhanced_prompt
    logging.info(f"Original prompt: {request.prompt}")
    logging.info(f"Enhanced prompt: {enhanced_prompt}")

    # Call Text-to-Image app
    image_data = None
    if text_to_image_app_id:
        try:
            logging.info(f"Attempting to call Text-to-Image app. Target App ID: {text_to_image_app_id}. Available connections: {list(stub._connections.keys()) if stub._connections else 'No connections'}")
            # logging.info(f"Calling Text-to-Image app with ID: {text_to_image_app_id}...") # Original log, can be removed or kept
            app_response = stub.call(
                app_id=text_to_image_app_id,
                data={'prompt': enhanced_prompt},
                uid='super-user'
            )
            if app_response:
                image_data = app_response.get('result')
                if image_data:
                    logging.info(f"Image data type: {type(image_data)}")
                    logging.info(f"Image data size (approx): {len(image_data) if isinstance(image_data, (str, bytes)) else 'N/A'}")

                    # Save image data
                    try:
                        # Attempt to decode if base64, otherwise write raw bytes
                        if isinstance(image_data, str):
                            # Remove potential data URI prefix if present (e.g., "data:image/png;base64,")
                            if ',' in image_data:
                                image_data = image_data.split(',', 1)[1]
                            img_bytes = base64.b64decode(image_data)
                        elif isinstance(image_data, bytes):
                            img_bytes = image_data
                        else:
                            raise TypeError("Unsupported image data type")

                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                        image_filename = f"image_{timestamp}.png"
                        image_save_path = os.path.join("generated_assets", image_filename)

                        with open(image_save_path, 'wb') as f:
                            f.write(img_bytes)
                        logging.info(f"Image saved to {image_save_path}")
                        response.image_path = image_save_path  # Set image path in response
                        session_data['generated_image_path'] = response.image_path # Store in session
                    except (base64.binascii.Error, TypeError, FileNotFoundError) as e:
                        logging.error(f"Error saving image: {e}")
                        image_data = None # Ensure image_data is None if saving failed
                        response.image_path = None # Ensure path is None if saving failed
                        if 'generated_image_path' in session_data: # Clean up session data if saving failed
                            del session_data['generated_image_path']
                else:
                    logging.warning("No 'result' field in Text-to-Image app response.")
            else:
                logging.warning("Text-to-Image app call returned no response.")
        except Exception as e:
            logging.error(f"Error calling Text-to-Image app: {e}")
            image_data = None # Ensure image_data is None if T2I call failed
    else:
        logging.error("Text-to-Image app ID is not configured. Skipping Text-to-Image call.")
        # Initialize response message parts to indicate failure early
        response_message_parts = [f"Echo: {enhanced_prompt}. Text-to-Image app ID not configured."]


    # Initialize response message parts - moved here to handle T2I failure message
    if 'response_message_parts' not in locals(): # if not set by early T2I failure
        response_message_parts = [f"Echo: {enhanced_prompt}."]
        if not image_data and text_to_image_app_id : # If T2I app was called but failed to produce image_data
             response_message_parts.append("Failed to generate image.")


    if response.image_path: # Check if image was successfully saved
        response_message_parts = [f"Image generated for prompt: '{request.prompt}'. Saved as {response.image_path}."]

        # Call Image-to-3D app
        model_data = None
        if image_to_3d_app_id: # This condition already checks if image_to_3d_app_id is not None
            try:
                # The condition "image_data_for_3d" from prompt can be inferred if response.image_path exists,
                # as that's when we proceed. The outer 'if response.image_path:' handles this.
                logging.info(f"Attempting to call Image-to-3D app. Target App ID: {image_to_3d_app_id}. Available connections: {list(stub._connections.keys()) if stub._connections else 'No connections'}")
                # logging.info(f"Proceeding to Image-to-3D conversion with ID: {image_to_3d_app_id}...") # Original log

                # Prepare input for Image-to-3D app
                # We need to pass the raw image bytes, not the base64 string if it was decoded.
                # The image_data variable currently holds the original response from the T2I app.
                # We need to ensure we are sending the correct format (raw bytes or base64 string as expected by the I23D app)
                # For now, let's assume the I23D app expects a base64 encoded string if image_data is a string,
                # or raw bytes if image_data is bytes. This aligns with how we handled saving.

                image_input_for_3d = image_data # This could be str (base64) or bytes
                if isinstance(image_data, str):
                     # If it's a string, ensure it's the base64 part without data URI
                    if ',' in image_data:
                        image_input_for_3d = image_data.split(',', 1)[1]

                input_3d = {'image': image_input_for_3d}

                # logging.info(f"Calling Image-to-3D app with image data type: {type(image_input_for_3d)}") # Original log

                app_3d_response = stub.call(
                    app_id=image_to_3d_app_id,
                    data=input_3d,
                    uid='super-user'
                )

                if app_3d_response:
                    model_data = app_3d_response.get('result')
                    if model_data:
                        logging.info(f"3D model data type: {type(model_data)}")
                        logging.info(f"3D model data size (approx): {len(model_data) if isinstance(model_data, (str, bytes)) else 'N/A'}")

                        # Save 3D model data
                        try:
                            # Assuming model_data is bytes or base64 string
                            if isinstance(model_data, str):
                                # Remove potential data URI prefix if present
                                if ',' in model_data:
                                    model_data = model_data.split(',', 1)[1]
                                model_bytes = base64.b64decode(model_data)
                            elif isinstance(model_data, bytes):
                                model_bytes = model_data
                            else:
                                raise TypeError("Unsupported model data type for saving")

                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                        model_filename = f"model_{timestamp}.glb"
                        model_save_path = os.path.join("generated_assets", model_filename)

                        with open(model_save_path, 'wb') as f:
                            f.write(model_bytes)
                        logging.info(f"3D model saved to {model_save_path}")
                        response.model_path = model_save_path # Set model path in response
                        session_data['generated_model_path'] = response.model_path # Store in session
                        response_message_parts.append(f"3D model generated and saved as {response.model_path}.")
                        except (base64.binascii.Error, TypeError, FileNotFoundError) as e:
                            logging.error(f"Error saving 3D model: {e}")
                            response_message_parts.append("Failed to save 3D model.")
                            response.model_path = None # Ensure path is None if saving failed
                            if 'generated_model_path' in session_data: # Clean up session data if saving failed
                                del session_data['generated_model_path']
                    else:
                        logging.warning("No 'result' field in Image-to-3D app response.")
                        response_message_parts.append("Image-to-3D app returned no model data.")
                else:
                    logging.warning("Image-to-3D app call returned no response.")
                    response_message_parts.append("Image-to-3D app call failed.")
            except Exception as e:
                logging.error(f"Error calling Image-to-3D app: {e}")
                response_message_parts.append(f"Error during Image-to-3D conversion: {e}.")
        else:
            logging.warning("Image-to-3D app ID is not configured. Skipping Image-to-3D call.")
            response_message_parts.append("Image-to-3D app ID not configured, 3D model step skipped.")

    elif not image_data and text_to_image_app_id : # This means T2I was called but failed to produce image_data
        response_message_parts = [f"Echo: {enhanced_prompt}. Failed to generate image, so Image-to-3D step skipped."]
    elif not text_to_image_app_id: # This means T2I was never called due to missing ID
        # Message already set by the T2I block's else condition
        pass

    # Log session data (short-term memory)
    logging.info(f"Short-term memory for this session: {session_data}")
    # Save session data to file if image was generated (long-term memory)
    if session_data.get('generated_image_path'):
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            memory_file_name = f"session_{timestamp}.json"
            memory_file_path = os.path.join("memory_store", memory_file_name)
            with open(memory_file_path, 'w') as f:
                json.dump(session_data, f, indent=4)
            logging.info(f"Session data saved to {memory_file_path}")
        except Exception as e:
            logging.error(f"Error saving session data to JSON file: {e}")

    response.message = " ".join(response_message_parts)


############################################################
# LLM Prompt Enhancement function
############################################################
def enhance_prompt_with_llm(prompt: str) -> str:
    """
    Enhances the user's input prompt with predefined details.
    Simulates an LLM prompt enhancement.
    """
    enhancement = ", detailed, vibrant, 4k, cinematic lighting"
    return prompt + enhancement