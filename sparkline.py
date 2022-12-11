import io
import base64
from matplotlib.figure import Figure

FIG_WIDTH = round(100 / 96, 3) # 120px @ 96dpi
FIG_HEIGHT = round(30 / 96, 3) # 35px @ 96dpi

def get_b64_linegraph(X, Y, color='green') -> str:
    fig = Figure(figsize=(FIG_WIDTH, FIG_HEIGHT))
    ax = fig.add_subplot()
    ax.plot(X, Y, color=color)
    ax.grid(False)
    ax.set_title('')
    ax.set_alpha(0.0)
    ax.get_yaxis().set_visible(False)
    ax.get_xaxis().set_visible(False)
    ax.axis('off')

    # Save the sparkline to a temporary buffer
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)

    # Encode the byte array as a Base64 image string
    return base64.b64encode(buf.read())