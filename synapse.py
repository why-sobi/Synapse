# %%
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from pathlib import Path
import subprocess
import shutil
import json
import sys
import os
import glob

script_dir = Path(__file__).parent.resolve()
load_dotenv(script_dir / ".env")

# %%
prompt_template = """
Act as a build engineer for Windows. 
For project name: {project_name}
For each library: {libraries}

Rules:
1. For each library provide the following details in format:
   > Format: Clone URL|Header-only(0/1)|Build Tags (disable tests if possible & build type = {build_type} and static building, if applicable)
   > Example: https://github.com/fmtlib/fmt|0|-DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF -DBUILD_TESTS=OFF -DBUILD_EXAMPLES=OFF -DBUILD_BENCHMARKS=OFF 
2. URL can be from github or gitlab. (depeding on where the stable version of the library is hosted)
3. Separate each library's details with a newline.  
4. Keep in mind, if header-only = 1, no builds will take place for that library.
5. Build Tags should include any relevant cmake options to disable tests/examples and set build type.
Finally, provide a CmakeLists.txt with appropriate find_package, target_include_directories, add_executable etc commands (no FetchContent, add_subdirectory... etc) for each library.

NOTE: Separate both sections with '---CMAKE---' string.

---CMAKE--- Section Rules:
1. Include 'if(MSVC) add_compile_options(/utf-8) endif()' to prevent Unicode errors.
2. Use 'list(APPEND CMAKE_PREFIX_PATH ...)' for each library pointing to its 'external/LibName/build/install' folder.
3. Use 'find_package(LibName CONFIG REQUIRED)' for compiled (0) libraries.
4. Use 'file(GLOB_RECURSE SOURCES "src/*.cpp" "src/*.c")' to gather source files. (IMP NOTE: This should always be done before library linking)
5. Use 'target_include_directories' for header-only (1) libraries pointing to 'external/LibName/include'.
6. Do NOT use FetchContent or add_subdirectory.
7. Should be made keeping build flags in mind (like static or not etc ...).
8. Ensure the CMakeLists.txt is complete and ready to use as PER LIBRARY linking and includes.

Final Output Format:
URL|0/1|build tags
URL|0/1|build tags
URL|0/1|build tags
---CMAKE---
CMakeLists.txt content here

    
-----------------IMPORTANT----------------- 
> Do not add any extra text or explanation.
> Build tags should be library specific cmake options. (e.g., for fmt, use -DFMT_TEST=OFF)
> All links will be cloned into 'external' directory. 
> Install will be inside the library's build/install directory. (no install for header-only libraries)
> You are responsible for ensuring the correctness of the CMakeLists.txt. (linking and includes)
> Ensure the CMakeLists.txt is complete and ready to use. (will be in root directory)

Dir structure for reference:
root/
|-- CMakeLists.txt
|-- external/
   |- Library1/
      |- build/
         |- install/
            |- include
            |- lib
   |- Library2
|- include
|- src (all .c/.cpp files here should be added to the executable target recursively)


------------ SPECIAL LIBRARY INSTRUCTIONS -------------
1. For SFML 
    > For find_package use Sentence case for packages name e.g System, Window, Graphics etc insead of system, window etc.
    > Static Linking on in Cmake as well. (add set(SFML_STATIC_LIBRARIES TRUE) before find_package)
    > Link target SFML::System ... instead of sfml-system etc. (same for other components)
2. For Boost, only include the necessary components (e.g., filesystem, system etc)
3. For OpenCV, ensure to link against the opencv_world library.
-------------------------------------------"""


def get_available_generators():
    options = []
    vswhere = os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe")
    vs_install_path = None

    if os.path.exists(vswhere):
        cmd = [vswhere, "-products", "*", "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-format", "json", "-prerelease"]
        try:
            installations = json.loads(subprocess.check_output(cmd, text=True))
            for inst in installations:
                vs_install_path = inst.get("installationPath")
                ver_major = inst.get("installationVersion", "").split(".")[0]
                
                # Find the actual cl.exe path for x64
                # We use glob because the intermediate toolset version folder name varies
                msvc_tools_path = os.path.join(vs_install_path, r"VC\Tools\MSVC")
                cl_search_path = os.path.join(msvc_tools_path, r"**\bin\Hostx64\x64\cl.exe")
                cl_exe_list = glob.glob(cl_search_path, recursive=True)
                
                if not cl_exe_list:
                    continue
                
                # Pick the latest toolset found
                cl_exe = cl_exe_list[-1]
                
                if ver_major == "18":
                    gen_name = "Visual Studio 18 2026"
                    options.append({
                        "id": "msvc",
                        "display": f"MSVC 2026 ({inst['installationVersion']})",
                        "generator": gen_name,
                        "flags": ["-A", "x64"], # VS Generator handles compiler path via -A
                        "needs_dev_shell": False
                    })

                    vs_ninja = os.path.join(vs_install_path, r"Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe")
                    if os.path.exists(vs_ninja):
                        options.append({
                            "id": "ninja_msvc",
                            "display": "Ninja (using MSVC 18.1)",
                            "generator": "Ninja",
                            "flags": [
                                f"-DCMAKE_MAKE_PROGRAM={vs_ninja}",
                                f"-DCMAKE_CXX_COMPILER={cl_exe}", # Ensure cl_exe points to Hostx64/x64
                            ],
                            "needs_dev_shell": True 
                        })
        except: pass

    # 2. Check for MinGW
    mingw_gpp = shutil.which("g++")
    if mingw_gpp:
        options.append({
            "id": "mingw",
            "display": "MinGW Makefiles",
            "generator": "MinGW Makefiles",
            "flags": [
                "-DCMAKE_SH=CMAKE_SH-NOTFOUND",
                f"-DCMAKE_CXX_COMPILER={mingw_gpp}"
            ],
            "needs_dev_shell": False
        })
        
        if vs_install_path:
             vs_ninja = os.path.join(vs_install_path, r"Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe")
             if os.path.exists(vs_ninja):
                 options.append({
                    "id": "ninja_mingw",
                    "display": "Ninja (using MinGW)",
                    "generator": "Ninja",
                    "flags": [
                        f"-DCMAKE_MAKE_PROGRAM={vs_ninja}", 
                        f"-DCMAKE_CXX_COMPILER={mingw_gpp}"
                    ],
                    "needs_dev_shell": False
                })

    return options

def select_gererator():
    options = get_available_generators()
    print("Available Generators:")
    for idx, opt in enumerate(options):
        print(f"{idx + 1}. {opt['display']}")
    
    choice = int(input("Select a generator by number: ")) - 1
    if 0 <= choice < len(options):
        return options[choice]
    else:
        print("Invalid choice. Exiting.")
        sys.exit(1)


# %%
def create_project_structure(project_name):
    # 1. Define the base project directory
    base_dir = Path(project_name).resolve()
    
    # 2. List the subfolders you want
    subfolders = ["external", "include", "src"]
    
    # 3. Create the folders
    for folder in subfolders:
        # Join base_dir with the subfolder
        target_path = base_dir / folder
        
        # parents=True: Creates the project_name folder if it doesn't exist
        # exist_ok=True: Doesn't crash if the folder is already there
        target_path.mkdir(parents=True, exist_ok=True)
    
    (base_dir / "src" / "main.cpp").touch()  # Create an empty main.cpp file in src
    main_content = """#include <iostream>
    int main() {
        std::cout << "Hello, World!" << std::endl;
        return 0;
        }"""
    with open(base_dir / "src" / "main.cpp", "w") as f:
        f.write(main_content)
        
    print(f"Created project structure at: {base_dir}")
    return base_dir

# %%
def get_response(lib: list[str], project_name: str, build_type: str = "Release"):
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0) 
    response = model.invoke(prompt_template.format(libraries=", ".join(lib), project_name=project_name, build_type=build_type))
    return response.content

# %%
def setup_project(project_name: str, response: str, generator: dict):
    root = create_project_structure(project_name=project_name)
    libs_config, cmake_content = response.split('---CMAKE---')
    
    for lib_config in libs_config.strip().split('\n'):
        url, header_only, build_tags = lib_config.split('|')
        print(f"\n[INPUT] URL: {url}, Header-Only: {header_only}, Build Tags: {build_tags}")
        external_dir = root / "external"
        folder_dir = external_dir / Path(url).stem
        
        folder_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n> Cloning: {url}\n")
        # cloning
        # The '--depth 1' flag tells Git to only pull the latest snapshot, not the whole history
        subprocess.run(["git", "clone", "--depth", "1", url, str(folder_dir)], check=True)
        
        if header_only == "1":
            print(f"{url} is header-only. Skipping build.")
            continue
        
        print(f"> Building with tags: {build_tags}")
        # building
        lib_path = external_dir / Path(url).stem
        build_path = lib_path / "build"
        build_path.mkdir(parents=True, exist_ok=True)
        
        
        build_cmd = ["cmake", "..", "-G", generator["generator"]]
        build_cmd.extend(generator["flags"])
        if build_tags.strip():
            build_cmd.extend(build_tags.strip().split(' '))
        build_cmd.append("-DCMAKE_INSTALL_PREFIX=./install")
        
        try:
            subprocess.run(
                build_cmd,
                cwd=build_path, 
                shell=False, 
                check=True
            )
        except subprocess.CalledProcessError as e:
            print(f"--- FAILED TO CONFIGURE {url} ---")
            print(e)
            continue
        
        print(f"Installing...")
        # install
        subprocess.run("cmake --build . --target install --parallel" , cwd=build_path, shell=True, check=True)
    
    # Save CMakeLists.txt
    cmake_file_path = root / "CMakeLists.txt"
    with open(cmake_file_path, "w") as f:
        f.write(cmake_content)
    print(f"CMakeLists.txt created at {cmake_file_path}")


def compile_project(project_name: str, generator: dict, build_type: str = "Release"):
    root = Path(project_name).resolve()
    build_path = root / "build"
    build_path.mkdir(parents=True, exist_ok=True)
    
    # 1. Configuration Command
    # Added -DCMAKE_BUILD_TYPE here
    configure_cmd = [
        "cmake", "..", 
        "-G", generator["generator"],
        f"-DCMAKE_BUILD_TYPE={build_type}" 
    ]
    configure_cmd.extend(generator["flags"])
    
    try:
        print(f"--- CONFIGURING PROJECT: {project_name} ({build_type}) ---")
        subprocess.run(
            configure_cmd,
            cwd=build_path, 
            shell=False, 
            check=True
        )
        
        # 2. Actual Build Command (The "Compile" step)
        print(f"--- BUILDING PROJECT: {project_name} ---")
        compile_cmd = ["cmake", "--build", ".", "--config", build_type]
        
        subprocess.run(
            compile_cmd,
            cwd=build_path,
            shell=False,
            check=True
        )
        
        print(f"✅ Successfully built {project_name}")

    except subprocess.CalledProcessError as e:
        print(f"--- FAILED TO BUILD PROJECT {project_name} ---")
        print(f"Command: {e.cmd}")
        return

def main():
    if len(sys.argv) < 3:
        print("!!!ERROR!!! \nUsage: synapse <project_name> <library1,library2,...> [build_type]")
        return
    project_name = sys.argv[1]
    libraries = sys.argv[2].split(',')
    build_type = sys.argv[3] if len(sys.argv) > 3 else "Release"
    generator = select_gererator()
    
    if generator["needs_dev_shell"] and not "VCINSTALLDIR" in os.environ:
        print("⚠️  WARNING: You are NOT in a Developer Command Prompt.")
        print("Ninja + MSVC builds will likely fail.")
        
        sys.exit(1)
    
    response = get_response(libraries, project_name, build_type)
    
    print(f"-------------------------Response from model retreived:-------------------------\n")
    for line in response.split('\n'):
        print(line)
    print(f"\n-------------------------Setting up project: {project_name}-------------------------\n")
    setup_project(project_name, response, generator)
    
    print(f"Project {project_name} setup completed.")
    
    print(f"Compiling the Project: {project_name}...\n")
    compile_project(project_name, generator, build_type)
    return
    
if __name__ == "__main__":
    main()

# %%
