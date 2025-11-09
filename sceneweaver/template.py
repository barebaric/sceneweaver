TEMPLATE_YAML = """
settings:
  width: 1920
  height: 1080
  fps: 30
  output_file: output.mp4
  # Default font for all text elements. Can be a font name your system
  # recognizes (e.g., "Arial") or a path to a .ttf file.
  font: DejaVuSans
  # Default sub-folder for storing newly recorded audio.
  audio_recording_path: audio

scenes:
  - type: template
    name: title_and_subtitle
    id: intro_card
    with:
      title: My Awesome Video
      subtitle: A subtitle describing the content
      # You can optionally override the default accent color
      # accent_color: "#FFC300"
      duration: 5
    cache:
      max-size: 1GB
    # To record audio for this scene, run:
    # sceneweaver scene audio spec.yaml:intro_card
    audio:
      - file: audio/intro_card.wav
        shift: -0.5 # Start audio 0.5s before scene begins

  - type: image
    id: main_content
    duration: 10
    image: ~/path/to/your/screenshot.png
    stretch: false   # retain aspect ratio
    width: 80  # percent of screen
    position: center
    annotations:
      - type: highlight
        rect: [20, 20, 25, 10] # [x, y, width, height] in percent
        color: "#f0f0f0"
        opacity: 0.4
      - type: text
        location: bottom
        content: This caption uses the default font.
      - type: text
        position: [10, 10]
        content: This one uses a custom font.
        # You can also override the font for a specific annotation
        font: Courier-New
        color: yellow
        fontsize: 48
    transition:
      type: cross-fade
      duration: 2

  - type: image
    id: short_image
    frames: 90 # This will be 3 seconds at 30fps
    image: ~/path/to/your/second_image.png

  - type: video
    id: clip_1
    file: ~/path/to/your/video.mp4
    cache:
      max-size: 5GB
    # Audio specified here will REPLACE the video's original audio.
    # audio:
    #   - file: audio/my_narration.mp3

  - type: video-images
    id: image_sequence
    fps: 25
    file: ~/path/to/frames/*.png
    cache: true
    effects:
      - type: fade-out
        duration: 1
"""

TEMPLATE_BOILERPLATE_YAML = """
# This is a boilerplate template.yaml file for a new SceneWeaver template.
#
# A template provides a set of default values for scenes.
# The user can then override any of these defaults directly in their spec file.
#
# EXAMPLE:
# This template defines 'duration: 5'. A user can override this by writing
# 'duration: 10' on the template block in their main spec file.

# A template should NOT define an 'id'. This must be set by the user.

- type: svg
  # Defaults for the template
  duration: 5
  template: "template.svg" # Asset paths are relative to this file.

  # Parameters to be filled by the 'with:' block
  params:
    line1: "{{ line1 | default('Default Line 1') }}"
    line2: "{{ line2 | default('Default Line 2') }}"
"""
