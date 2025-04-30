from AudioAnalyzer import *
import random
import colorsys


def rnd_color():
    """Return a random RGB colour (0-255 each) using HLS space for pleasant hues."""
    h, s, l = random.random(), 0.5 + random.random() / 2.0, 0.4 + random.random() / 5.0
    return [int(256 * i) for i in colorsys.hls_to_rgb(h, l, s)]

# ────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────

filename = "./audio/drake.mp3"  # <- change to any .wav / .mp3 supported by librosa

# starting colours
circle_color          = (40, 40, 40)
polygon_default_color = rnd_color()          # now random on launch!
polygon_bass_color    = polygon_default_color.copy()
polygon_color_vel     = [0, 0, 0]

min_decibel, max_decibel = -80, 80
bass_trigger             = -30  # dB threshold for kicks

# geometry
min_radius, max_radius = 100, 150
radius, radius_vel     = min_radius, 0

# frequency bands
bass       = {"start": 50,   "stop": 100,  "count": 12}
heavy_area = {"start": 120,  "stop": 250,  "count": 40}
low_mids   = {"start": 251,  "stop": 2000, "count": 50}
high_mids  = {"start": 2001, "stop": 6000, "count": 20}

freq_groups = [bass, heavy_area, low_mids, high_mids]

# ────────────────────────────────────────────────
# INIT
# ────────────────────────────────────────────────

analyzer = AudioAnalyzer()
analyzer.load(filename)

pygame.init()
infoObject = pygame.display.Info()
screen_w   = int(infoObject.current_w / 2.2)
screen_h   = int(infoObject.current_w / 2.2)

audio_pos  = 0.0  # cached seconds value to avoid repeat get_pos calls

# Set up the drawing window
screen  = pygame.display.set_mode([screen_w, screen_h])
clock   = pygame.time.Clock()

circleX, circleY = screen_w // 2, screen_h // 2

# ────────────────────────────────────────────────
# BAR GENERATION
# ────────────────────────────────────────────────

bars, tmp_bars, length = [], [], 0

for group in freq_groups:
    group_bars = []
    span       = group["stop"] - group["start"]
    count      = group["count"]
    remainder  = span % count
    step       = span // count
    start_freq = group["start"]

    for _ in range(count):
        extra = 2 if remainder > 0 else 1
        if remainder > 0:
            remainder -= 1
        rng  = np.arange(start=start_freq, stop=start_freq + step + extra)
        start_freq += step + extra
        group_bars.append(rng)
        length += 1

    tmp_bars.append(group_bars)

angle_dt = 360 / length
ang      = 0
for group_bars in tmp_bars:
    grp = []
    for rng in group_bars:
        colour = rnd_color()  # ← every spoke now has its own colour
        bar = RotatedAverageAudioBar(
            circleX + radius * math.cos(math.radians(ang - 90)),
            circleY + radius * math.sin(math.radians(ang - 90)),
            rng,
            colour,
            angle=ang,
            width=8,
            max_height=370,
        )
        grp.append(bar)
        ang += angle_dt
    bars.append(grp)

pygame.mixer.music.load(filename)
pygame.mixer.music.play(loops=0)

bass_trigger_started = 0
poly_color           = polygon_default_color.copy()
running              = True

while running:
    dt = clock.tick(60) / 1000.0  # seconds since last frame (~16 ms at 60 FPS)
    screen.fill(circle_color)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # update audio time once per frame
    audio_pos = pygame.mixer.music.get_pos() / 1000.0

    # update all bars & compute average bass
    avg_bass = 0
    for band in bars:
        for bar in band:
            bar.update_all(dt, audio_pos, analyzer)
    for bar in bars[0]:  # first group is bass
        avg_bass += bar.avg
    avg_bass /= len(bars[0])

    if avg_bass > bass_trigger:  # strong kick
        if bass_trigger_started == 0:
            bass_trigger_started = pygame.time.get_ticks()
        if (pygame.time.get_ticks() - bass_trigger_started) / 1000.0 > 2:
            polygon_bass_color = rnd_color()  # new pulse colour every 2 s of sustained bass
            bass_trigger_started = 0
        if polygon_bass_color is None:
            polygon_bass_color = rnd_color()

        target_radius = min_radius + int(avg_bass * ((max_radius - min_radius) / (max_decibel - min_decibel)) + (max_radius - min_radius))
        radius_vel    = (target_radius - radius) / 0.15
        polygon_color_vel = [(polygon_bass_color[i] - poly_color[i]) / 0.15 for i in range(3)]

    elif radius > min_radius:  # relax back
        bass_trigger_started = 0
        polygon_bass_color   = rnd_color()
        radius_vel           = (min_radius - radius) / 0.15
        polygon_color_vel    = [(polygon_default_color[i] - poly_color[i]) / 0.15 for i in range(3)]

    else:  # idle
        bass_trigger_started = 0
        poly_color           = polygon_default_color.copy()
        polygon_bass_color   = rnd_color()
        polygon_color_vel    = [0, 0, 0]
        radius_vel           = 0
        radius               = min_radius

    # apply easing
    radius     += radius_vel * dt
    for i in range(3):
        poly_color[i] = int(clamp(0, 255, poly_color[i] + polygon_color_vel[i] * dt))

    # position bars on current circle radius
    poly = []
    for band in bars:
        for bar in band:
            bar.x = circleX + radius * math.cos(math.radians(bar.angle - 90))
            bar.y = circleY + radius * math.sin(math.radians(bar.angle - 90))
            bar.update_rect()
            poly.extend([bar.rect.points[3], bar.rect.points[2]])

    # draw
    pygame.draw.polygon(screen, poly_color, poly)
    pygame.draw.circle(screen, circle_color, (circleX, circleY), int(radius))

    pygame.display.flip()

pygame.quit()