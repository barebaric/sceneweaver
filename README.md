# SceneWeaver

SceneWeaver is a command-line tool for creating videos from a declarative YAML specification.
Under the hood, it uses MoviePy to render and assemble scenes, allowing for repeatable and
version-controllable video production.

For larger projects it supports modular composition and caching, and you can include other
videos as well.

## Installation

```bash
sudo apt install ffmpeg portaudio19-dev     # Ubuntu 24.04. May be different on other distros
pip install sceneweaver
```

## Usage

### Starting

First, create a new specification file to define your video's structure.

```bash
sceneweaver create my_video.yaml    # creates a new template you can edit
sceneweaver generate my_video.yaml
```

### Example specification

Here is a basic example of a `my_video.yaml` file:

```yaml
settings:
  width: 1920
  height: 1080
  fps: 30
  output_file: "output.mp4"

scenes:
  - id: intro_card
    type: title_card
    duration: 3  # optional if audio is given
    audio: my/narration.wav
    title: Hello, SceneWeaver!
    transition:
      type: cross-fade
      duration: 1

  - id: main_image
    type: image
    duration: 10
    image: "~/path/to/your/image.png"
    stretch: false # Preserves aspect ratio
    width: 80 # As 80% of the screen width
    annotations:
      - type: text
        location: bottom
        content: This is a caption for the image.
    cache:
      max-size: "2GB"
    transition:
      type: cross-fade
      duration: 2

  - id: outro
    type: video
    fps: 25
    file: something.mp4
    effects:
      - type: fade-out
        duration: 1
```

### Other Commands

#### Managing Scenes

SceneWeaver provides interactive commands to help you build your spec file quickly.

- **Add a new scene:**

  ```bash
  # Interactively prompts for ID, type, and required info
  sceneweaver scene add my_video.yaml

  # Directly specify the new scene's ID and type
  sceneweaver scene add my_video.yaml:new_intro title_card
  ```

- **Record audio for a scene:**

  ```bash
  # Interactively prompts to select a scene to record for
  sceneweaver scene audio my_video.yaml

  # Directly target a scene by its ID
  sceneweaver scene audio my_video.yaml:main_image
  ```

#### Rendering and Cache

- **Render a single scene** (for quick previews):

  ```bash
  sceneweaver generate my_video.yaml:intro_card
  ```

- **Force re-rendering** (ignoring the cache):

  ```bash
  sceneweaver generate my_video.yaml --force
  ```

- **Clear the cache** of all previously rendered scenes:
  ```bash
  sceneweaver clean
  ```

## Development

This project uses [Pixi](https://pixi.sh/) for environment and task management.

- **Setup the environment:**

  ```bash
  pixi install
  ```

- **Run the app:**

  ```bash
  pixi run sceneweaver my_template.yaml
  ```

- **Common tasks** (run with `pixi run <task>`):
  - `test`: Run the test suite.
  - `lint`: Run all linters (flake8, pyflakes, pyright).
  - `format`: Format the code using Ruff.
