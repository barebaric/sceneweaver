TEMPLATE_YAML = """
settings:
  width: 1920
  height: 1080
  fps: 30
  output_file: output.mp4
  # Default font for all text elements. Can be a font name your system
  # recognizes (e.g., "Arial") or a path to a .ttf file.
  font: DejaVuSans

scenes:
  - type: title_card
    id: intro_card
    duration: 5
    title: My Awesome Video
    subtitle: A subtitle describing the content
    # You can override the font for a specific scene
    # font: Impact
    cache:
      max-size: 1GB

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

  - type: image
    id: short_image
    frames: 90 # This will be 3 seconds at 30fps
    image: ~/path/to/your/second_image.png

  - type: video
    id: clip_1
    file: ~/path/to/your/video.mp4
    cache:
      max-size: 5GB

  - type: video-images
    id: image_sequence
    fps: 25
    file: ~/path/to/frames/*.png
    cache: true
"""
