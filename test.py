import plotly.graph_objects as go
fig = go.Figure(data=go.Bar(y=[2, 3, 1]))
fig.to_image(format="png")  # This should now succeed

# 
print("Plotly image conversion works correctly.")