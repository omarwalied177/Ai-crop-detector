# Final model: architecture and measured results

Date: 28 November 2026. This note is the reference for the numbers quoted in the
README and in the Drive milestone documents.

## Which run this is

The final model is the `balsample` (balanced sampling) variant from the Stage 3 run on
the friend's Kaggle account (`mohamedmohamed778/final-omar`), finished 28 November 2026
after 1h47m on a GPU. Four class-balance recipes were trained in the same run and
compared on the same test sets: balanced sampling, class weights, no balancing, and the
earlier v6 model.

The run has 53 crop+disease classes in the training pool, across 12 crops, with disease
heads for 11 crops. Squash has no disease head. No new classes were added relative to
the earlier run.

## Architecture

| Part | Detail |
|---|---|
| Encoders | CLIP ViT-L/14-336, DINOv2-Large, SigLIP-so400m-384 |
| Adaptation | LoRA on DINOv2, r=8, alpha=16, targets query and value. LoRA validation accuracy 0.693. |
| Heads | 12-crop router, then one disease head per crop (11 heads) |
| Balance | Sampling balanced by class, source and image group |

## Results

Accuracy on held-out test sets:

| Test set | balsample | class weights | no balancing | previous v6 |
|---|---|---|---|---|
| PlantDoc test | 86.9% | 86.4% | 87.0% | 86.4% |
| PlantSeg unseen | 85.6% | 86.7% | 85.1% | 85.4% |
| PlantVillage | 99.2% | 99.2% | 99.2% | 99.2% |

## How to read them

- Every difference between the four recipes is under 1.5 points, which is noise on
  test sets this small. Balanced sampling was kept because it was best on the unseen
  field set; it is not a proven improvement.
- The one clear improvement from this run is potato late blight: 82% against 71%
  before, on 14 test photos.
- The field test sets are small. One photo moves a class score by 5 to 10 points, so
  per-class ordering is rough and the overall figure is an estimate.
- The model is still unproven on fresh photos that nobody tuned on. A final check on
  about 100 new labelled photos is the missing step.

## Weakest classes

| Class | Accuracy | Test photos | Training photos |
|---|---|---|---|
| Blueberry rust | 61% | 9 | 77 |
| Grape leaf spot | 64% | 18 | 150 |
| Potato late blight | 75% | 14 | 150+ |
| Cherry leaf spot | 76% | 21 | 150 |
| Grape downy mildew | 77% | 50 | 150 |
| Tomato early blight | 79% | 24 | 150+ |
| Potato early blight | 80% | 10 | 150+ |
| Corn gray leaf spot | 82% | 14 | 150+ |

Classes with under 80 training photos: raspberry leaf spot (36), cherry powdery mildew
(57), raspberry fire blight (68), strawberry leaf scorch (65), blueberry botrytis (72),
raspberry yellow rust (74), blueberry rust (77). The raspberry classes and blueberry
botrytis have no test photos, so their accuracy is unknown.

## Weights

Private Hugging Face model repo `omarwalied/ai-crop-doctor-weights`, folder `balsample`,
about 199 MB:

```
router.pt              crop router, 12 crops
heads/*.pt             11 per-crop disease heads
dinov2_lora_state.pt   LoRA adapter for DINOv2
config.json            variant, LoRA settings, router classes
class_lists.json       class names per head
```

The repository is private. Access needs a Hugging Face read token with access to the
repo.

## Superseded numbers

- The Milestone 5 deck (23 November) reports the earlier CLIP + DINOv2 run:
  PlantWild 85.1%, PlantDoc 80.6%, PlantVillage 99.6%. That deck also used 2,816-dim
  features and no SigLIP or LoRA. The architecture description there is still accurate
  for that run, but the numbers are not the final model's.
- The Milestone 2 report is a different model family: MobileNetV3Large, 38 classes,
  98.6% on a held-out PlantVillage-style split. It is a lab benchmark for that
  milestone, not field performance.
