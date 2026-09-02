"""Train Chest CT-Scan model using KaggleHub dataset download."""

import argparse
from modules.ai_layer import DiseasePredictor


def main():
    parser = argparse.ArgumentParser(description="Train Chest CT-Scan detection model")
    parser.add_argument("--epochs", type=int, default=20, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    parser.add_argument(
        "--model-type",
        choices=["mobilenet", "simple_cnn"],
        default="mobilenet",
        help="Model architecture"
    )
    parser.add_argument(
        "--save-model",
        default="models/chest_ctscan_model.keras",
        help="Output model path"
    )
    parser.add_argument(
        "--no-fine-tune",
        action="store_true",
        help="Disable MobileNet fine-tuning stage"
    )
    parser.add_argument(
        "--download-retries",
        type=int,
        default=3,
        help="Retry count for Kaggle download if network disconnects"
    )
    parser.add_argument(
        "--dataset-dir",
        default="",
        help="Optional local dataset directory to skip Kaggle download"
    )
    args = parser.parse_args()

    predictor = DiseasePredictor()
    if args.dataset_dir:
        dataset_dir = DiseasePredictor.find_dataset_directory(args.dataset_dir)
        result = predictor.train_from_directory(
            dataset_dir=dataset_dir,
            epochs=args.epochs,
            batch_size=args.batch_size,
            model_type=args.model_type,
            save_model_path=args.save_model,
            fine_tune=not args.no_fine_tune,
            expected_classes=None
        )
    else:
        result = predictor.train_chest_ctscan_model(
            epochs=args.epochs,
            batch_size=args.batch_size,
            model_type=args.model_type,
            save_model_path=args.save_model,
            fine_tune=not args.no_fine_tune,
            download_retries=args.download_retries
        )

    print("Training complete")
    print(f"Dataset dir: {result['dataset_dir']}")
    print(f"Classes: {result['classes']}")
    print(f"Train accuracy: {result['train_accuracy']:.4f}")
    print(f"Validation accuracy: {result['val_accuracy']:.4f}")
    print(f"Saved model: {result['saved_model']}")


if __name__ == "__main__":
    main()
