
# Session-Based Recommendation Demo

## 1. Objective

Build a demo for the Big Data project to demonstrate
session-based next-item recommendation.

The demo will allow users to select a session and
view the Top-20 product recommendations generated
by the models.

## 2. Project Scope

- Dataset: eCommerce Behavior Data (October 2019)
- Models: Popularity, GRU, XLNet
- Input: Sequence of product IDs in a user session
- Output: Top-20 ranked product recommendations
- Ground truth: Actual next item
- Metrics: Recall@20 and NDCG@20

## 3. Planned Demo Workflow

1. Select a session from the evaluation dataset.
2. Display the session's input product sequence.
3. Select a model (Popularity, GRU, or XLNet).
4. Load the model's prediction output.
5. Display the Top-20 ranked recommendations.
6. Highlight the actual next item if it appears
   in the recommendations.

## 4. Model Integration

The demo will use prediction outputs or inference
artifacts provided by TV2.

The input/output JSON format will be confirmed
with TV2 before implementation.

The demo will not train or fine-tune models.

## 5. User Interface

UI framework: Not decided yet.

Possible options:
- Streamlit
- Gradio
- Web interface

## 6. Dependencies

- TV1: Processed session data and product mapping
- TV2: Prediction schema and inference output
- TV3: Runtime/environment support if required

## 7. Current Status

- [x] Demo structure created
- [x] README outline created
- [ ] Prediction schema confirmed
- [ ] Sample prediction file created
- [ ] UI implemented
- [ ] Model integration tested
