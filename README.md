# 🔮 Augury 3D Asset Library

A curated remote asset library for **Blender 5.2+** featuring procedural materials, Geometry Node toolkits, and production-ready assets.

---

## 🚀 Quick Setup

Connect the remote library directly to Blender in 3 quick steps:

1. In Blender, go to **Edit → Preferences → Asset Libraries**.
2. Click the **`+`** icon in the top-right corner and select **Add Remote Asset Library**.
3. Configure the library settings:
   * **Name:** `Augury Assets`
   * **URL:** `https://augury-b.github.io/blender-assets/`

---

## ⚙️ Recommended Import Method: **Append**

To tweak and inspect the node trees freely inside your scene:

* Open the **Asset Browser** in Blender.
* In the top bar, set **Import Method** to **`Append`** (or **`Append (Reuse Data)`**).
* **Why?** Remote assets stream on demand. Using **Append** creates an independent, fully editable datablock in your active `.blend` file so you can modify shader graphs, exposed geometry node sliders, and textures out of the box without breaking cached link references.

---

## 📂 Included Categories

* **Materials:** Procedural surface shaders, stylization setups, and non-photorealistic materials.
* **Geometry Nodes:** Parametric rigs, procedural asset generators, and modifier setups.
* **Models:** Production props and studio backdrops with auto-packed dependencies.
