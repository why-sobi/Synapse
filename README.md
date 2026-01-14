# SYNAPSE 

**The AI-Powered C++ Architect.** Stop fighting `CMakeLists.txt` and manual dependency hell. **Synapse** uses LLMs to intelligently scaffold C++ projects, resolve library dependencies, and configure your build environment in seconds.

---

## 🧠 Why Synapse?

C++ dependency management is notoriously difficult. Unlike `npm` or `pip`, C++ lacks a single unified repository. **Synapse** solves this by using AI to:

* **Discover:** Automatically find GitHub/GitLab URLs for any library you name.
* **Configure:** Generate the exact CMake flags needed for both Header-Only and Compiled libraries.
* **Isolate:** Keep your system clean by managing everything in a local `external/` folder.
* **Orchestrate:** Build dependencies and link them to your project without manual intervention.

---

## 🛠️ Usage

From your terminal, run:

```bash
python synapse.py [ProjectName] [Libraries,Separated,By,Commas] [BuildType]

```

### Example:

```bash
python synapse.py TestProject spdlog,nlohmann/json,fmt Release

```

---

## 🏗️ What happens "Under the Hood"?

1. **AI Discovery:** Synapse sends your library list to an LLM to retrieve the best Git URLs and required CMake configuration tags.
2. **Scaffolding:** Creates a standard directory structure:
* `src/`: Your source code.
* `external/`: Cloned dependencies.
* `build/`: CMake build artifacts.


3. **Dependency Build:** For compiled libraries, Synapse runs a local `cmake --build` and `install` step to ensure binaries match your local compiler (MinGW/MSVC).
4. **Linkage:** Generates a custom `CMakeLists.txt` that correctly handles `target_link_libraries` for compiled libs and `target_include_directories` for header-only libs.

---

## 📦 Requirements

* **Python 3.x**
* **CMake 3.15+**
* **A C++ Compiler** (MinGW, MSVC, or Clang)
* **AI API Key** (Configured in the script)

---

## ⚠️ Disclaimer

Synapse uses LLMs to generate build configurations. While highly accurate for popular libraries like **Eigen**, **fmt**, and **JSON**, the AI may occasionally "hallucinate" a specific CMake flag. Always verify your `CMakeLists.txt` if a build fails.

---

### How to set this up as a "Real Tool"

1. **Add to PATH:** Add the folder containing `synapse.py` to your System Environment Variables.
2. **Alias it:** Rename the script or use a wrapper so you can just type `synapse` from any directory.
