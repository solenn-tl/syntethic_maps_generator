import os
import re

def file_exists(file_path):
    """
    Check if a file exists at the given path.

    Parameters:
    - file_path: str, the path of the file to check.

    Returns:
    - True if the file exists, False otherwise.
    """
    try:
        # Check if the path exists and is a file
        if os.path.isfile(file_path):
            #print("The file exists.")
            return True
        else:
            print("The file does not exist.")
            return False
    except Exception as e:
        # Handle any unexpected errors
        print(f"An error occurred: {e}")
        return False

def find_deep_folders_ign(base_dir, pattern):
    """
    Search for folders with a specific department code and navigate 3 levels deep 
    where the second-level folder contains '1_DONNEES_LIVRAISON' in its name.

    Parameters:
    - base_dir: str, the base directory containing the folders to search.
    - pattern: str, the department code to search for (e.g., 'D051').

    Returns:
    - List of matching third-level folder paths.
    """
    matching_folders = []
    # Iterate through folders in the base directory
    for folder_name in os.listdir(base_dir):

        # Check if the department code is in the folder name
        if pattern in folder_name:
            folder_path = os.path.join(base_dir, folder_name)
            first_level_path = folder_path

            # Check if the folder name matches the department pattern
            first_level_path = folder_path

            for folder_name_1 in os.listdir(first_level_path):
                second_level_path = os.path.join(first_level_path,folder_name_1)

                for folder_name_2 in os.listdir(second_level_path):
                    if "1_DONNEES_LIVRAISON" in folder_name_2:
                        third_level_path = os.path.join(second_level_path, folder_name_2)

                        for folder_name_3 in os.listdir(third_level_path):
                            fourth_level_path = os.path.join(third_level_path, folder_name_3)
    
    return fourth_level_path