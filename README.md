# Synapse

A small CLI script that uses an LLM to scaffold C++ projects so you don’t have to fight CMake every time you start something new.

It’s not a package manager.
It’s not smart.
It just saves time.

---

## What this is

Synapse automates the annoying part of starting a C++ project:

* Finding the right repo for a library
* Figuring out if it’s header-only or needs building
* Writing a usable CMakeLists.txt
* Setting up a clean folder structure
* Making sure things actually compile with your compiler
* Works with commom libraries

It uses an LLM to generate this info, then runs everything locally.

That’s it.

---

## What this is NOT

Let’s be clear:

* Not a replacement for vcpkg or Conan
* Not deterministic
* Not production-grade
* Not magic
* Not “AI that understands your project”

It’s an automation script that saves you from Googling and copy-pasting CMake snippets for 30 minutes.

---

## Why it exists

Because C++ setup is annoying.

Every time you want to:

* try a new library
* prototype something small
* test an idea

you end up:

* reading half-baked README files
* fighting CMake errors
* tweaking flags instead of writing code

Synapse just gets you to a compiling project faster.

---

## How it works

1. You give it a project name and some libraries
2. It asks an LLM for:

   * repo links
   * whether the library is header-only
   * common CMake setup
3. It creates:

   * `src/`
   * `external/`
   * `build/`
   * a CMakeLists.txt
4. It builds what needs building
5. You start coding

That’s all.

---

## Example

```bash
python synapse.py TestProject spdlog,nlohmann/json,fmt Release
```

Creates:

```
TestProject/
├── src/
├── external/
├── build/
└── CMakeLists.txt
```

---

## Requirements

* Python 3
* CMake 3.15+
* GCC / Clang / MSVC
* An API key (used to query the LLM)

---

## Limitations (read this)

* The LLM can hallucinate
* CMake flags may not always be perfect
* You may need to tweak things manually
* No version pinning
* No dependency resolution

If something breaks, you fix it like you would in a normal C++ project.

---

## Why I made it

I was tired of spending more time setting up projects than writing code.
This just removes that friction.
If it saves you time, it did its job.

---
