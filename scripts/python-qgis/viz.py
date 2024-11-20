df = merged_df

# Load the image
image = Image.open(image_path)

# Get image dimensions
image_width, image_height = image.size

# Create the plot
fig = go.Figure()

# Add the image as a background
fig.add_layout_image(
    dict(
        source=image,
        x=0,
        y=image_height,  # Plotly origin is bottom-left; adjust for top-left origin of the image
        xref="x",
        yref="y",
        sizex=image_width,
        sizey=image_height,
        xanchor="left",
        yanchor="top",
        layer="below",
    )
)

# Add polygons
for idx, row in merged_df.iterrows():
    polygon_coords = row["geometry"]
    
    # Convert string to list of coordinates
    polygon = ast.literal_eval(polygon_coords)

    x_coords, y_coords = zip(*polygon)  # Separate x and y coordinates
    fig.add_trace(
        go.Scatter(
            x=x_coords,
            y=[image_height - y for y in y_coords],  # Flip y-coordinates for image alignment
            mode="lines+text",
            fill="toself",  # Fill the polygon
            name=row["label"],  # Use label as the name
            textposition="top center",
            line=dict(color="red", width=2),
        )
    )

# Update layout
fig.update_layout(
    xaxis=dict(
        visible=False,
        range=[0, image_width],  # Match the image's width
    ),
    yaxis=dict(
        visible=False,
        range=[0, image_height],  # Match the image's height
    ),
    height=image_height,
    width=image_width,
    title="Annotations on Image",
)

# Display the plot
fig.show()
