"""Disease Predictor using CNN/MobileNet."""

import os
import json
import time
import importlib
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from .preprocessor import ImagePreprocessor

try:
    import kagglehub
    KAGGLEHUB_AVAILABLE = True
except ImportError:
    KAGGLEHUB_AVAILABLE = False

# Try to import TensorFlow dynamically (optional dependency)
try:
    tf = importlib.import_module("tensorflow")

    keras_models = importlib.import_module("tensorflow.keras.models")
    Model = keras_models.Model
    load_model = keras_models.load_model
    Sequential = keras_models.Sequential

    keras_layers = importlib.import_module("tensorflow.keras.layers")
    Dense = keras_layers.Dense
    Conv2D = keras_layers.Conv2D
    MaxPooling2D = keras_layers.MaxPooling2D
    Flatten = keras_layers.Flatten
    Dropout = keras_layers.Dropout
    GlobalAveragePooling2D = keras_layers.GlobalAveragePooling2D
    Input = keras_layers.Input

    keras_applications = importlib.import_module("tensorflow.keras.applications")
    MobileNetV2 = keras_applications.MobileNetV2

    keras_mobilenet_v2 = importlib.import_module("tensorflow.keras.applications.mobilenet_v2")
    mobilenet_preprocess = keras_mobilenet_v2.preprocess_input

    keras_optimizers = importlib.import_module("tensorflow.keras.optimizers")
    Adam = keras_optimizers.Adam

    TF_AVAILABLE = True
except ImportError:
    tf = None
    Model = None
    load_model = None
    Sequential = None
    Dense = None
    Conv2D = None
    MaxPooling2D = None
    Flatten = None
    Dropout = None
    GlobalAveragePooling2D = None
    Input = None
    MobileNetV2 = None
    mobilenet_preprocess = None
    Adam = None
    TF_AVAILABLE = False
    print("TensorFlow not installed. AI features will be limited.")


class DiseasePredictor:
    """
    AI model for disease detection from medical images.

    Supports:
    - Simple CNN (for starting)
    - MobileNetV2 (for better accuracy)
    - Custom trained models
    """

    # Default disease classes (can be customized)
    DEFAULT_CLASSES = [
        'Normal',
        'Pneumonia',
        'COVID-19',
        'Tuberculosis',
        'Other'
    ]
    BRAIN_MRI_DATASET = "navoneel/brain-mri-images-for-brain-tumor-detection"
    CHEST_XRAY_DATASET = "paultimothymooney/chest-xray-pneumonia"
    CHEST_CTSCAN_DATASET = "mohamedhanyyy/chest-ctscan-images"
    BREAST_ULTRASOUND_DATASET = "aryashah2k/breast-ultrasound-images-dataset"
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'}

    def __init__(self, model_path: str = None, classes: List[str] = None):
        """
        Initialize the predictor.

        Args:
            model_path: Path to pre-trained model (.h5 file)
            classes: List of class labels
        """
        self.model = None
        self.classes = classes or self.DEFAULT_CLASSES
        self.preprocessor = ImagePreprocessor(target_size=(224, 224))
        self.model_loaded = False
        self.preprocessing_mode = 'standard'
        self._base_model = None

        if model_path and os.path.exists(model_path):
            self.load_model(model_path)

    def create_simple_cnn(self, num_classes: int = None) -> Optional[object]:
        """
        Create a simple CNN model for disease classification.

        Args:
            num_classes: Number of output classes

        Returns:
            Keras Model
        """
        if not TF_AVAILABLE:
            print("TensorFlow required for CNN model")
            return None

        num_classes = num_classes or len(self.classes)

        model = Sequential([
            # Input layer
            Input(shape=(224, 224, 3)),

            # Conv Block 1
            Conv2D(32, (3, 3), activation='relu', padding='same'),
            MaxPooling2D((2, 2)),

            # Conv Block 2
            Conv2D(64, (3, 3), activation='relu', padding='same'),
            MaxPooling2D((2, 2)),

            # Conv Block 3
            Conv2D(128, (3, 3), activation='relu', padding='same'),
            MaxPooling2D((2, 2)),

            # Conv Block 4
            Conv2D(256, (3, 3), activation='relu', padding='same'),
            MaxPooling2D((2, 2)),

            # Flatten and Dense layers
            Flatten(),
            Dense(512, activation='relu'),
            Dropout(0.5),
            Dense(256, activation='relu'),
            Dropout(0.3),
            Dense(num_classes, activation='softmax')
        ])

        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )

        self.model = model
        self.model_loaded = True
        self.preprocessing_mode = 'standard'
        self._base_model = None
        return model

    def create_mobilenet_model(self, num_classes: int = None) -> Optional[object]:
        """
        Create a MobileNetV2-based model for better accuracy.

        Args:
            num_classes: Number of output classes

        Returns:
            Keras Model
        """
        if not TF_AVAILABLE:
            print("TensorFlow required for MobileNet model")
            return None

        num_classes = num_classes or len(self.classes)

        # Load MobileNetV2 without top layers
        base_model = MobileNetV2(
            weights='imagenet',
            include_top=False,
            input_shape=(224, 224, 3)
        )

        # Freeze base model layers
        base_model.trainable = False

        # Add custom classification layers
        inputs = Input(shape=(224, 224, 3))
        x = base_model(inputs, training=False)
        x = GlobalAveragePooling2D()(x)
        x = Dense(256, activation='relu')(x)
        x = Dropout(0.5)(x)
        outputs = Dense(num_classes, activation='softmax')(x)

        model = Model(inputs, outputs)

        model.compile(
            optimizer=Adam(learning_rate=0.0001),
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )

        self.model = model
        self.model_loaded = True
        self.preprocessing_mode = 'mobilenet'
        self._base_model = base_model
        return model

    def load_model(self, model_path: str, preprocessing_mode: str = None):
        """
        Load a pre-trained model.

        Args:
            model_path: Path to .h5 model file
        """
        if not TF_AVAILABLE:
            print("TensorFlow required to load models")
            return

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")

        self.model = load_model(model_path)
        self.model_loaded = True

        meta = self._load_model_metadata(model_path)
        if meta:
            loaded_classes = meta.get('classes', [])
            if loaded_classes:
                self.classes = loaded_classes
            self.preprocessing_mode = preprocessing_mode or meta.get('preprocessing_mode', 'standard')
        else:
            self.preprocessing_mode = preprocessing_mode or 'standard'

        self._base_model = None
        print(f"Model loaded from {model_path}")

    def save_model(self, model_path: str):
        """
        Save the current model.

        Args:
            model_path: Path to save the model
        """
        if self.model is None:
            raise ValueError("No model to save")

        folder = os.path.dirname(model_path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        self.model.save(model_path)
        self._save_model_metadata(model_path)
        print(f"Model saved to {model_path}")

    def predict(self, image_path: str) -> Dict:
        """
        Predict disease from medical image.

        Args:
            image_path: Path to medical image

        Returns:
            Dictionary with prediction results
        """
        if not self.model_loaded or self.model is None:
            # Return simulated prediction if no model
            return self._simulate_prediction(image_path)

        # Preprocess image according to model type
        if self.preprocessing_mode == 'mobilenet':
            img_array = self.preprocessor.preprocess_for_mobilenet(image_path)
        else:
            img_array = self.preprocessor.preprocess(image_path)

        # Make prediction
        predictions = self.model.predict(img_array, verbose=0)

        # Get top prediction
        predicted_idx = np.argmax(predictions[0])
        confidence = float(predictions[0][predicted_idx])

        # Get all class probabilities
        prediction_len = len(predictions[0])
        class_len = len(self.classes)
        usable_len = min(prediction_len, class_len)

        all_predictions = {
            self.classes[i]: float(predictions[0][i])
            for i in range(usable_len)
        }
        # Fallback labels if loaded model outputs more classes than configured labels.
        for i in range(usable_len, prediction_len):
            all_predictions[f'class_{i}'] = float(predictions[0][i])

        return {
            'predicted_class': self.classes[predicted_idx],
            'confidence': confidence,
            'all_predictions': all_predictions,
            'model_type': 'trained'
        }

    def _simulate_prediction(self, image_path: str) -> Dict:
        """
        Simulate prediction when no model is loaded.

        This is for demonstration purposes only.
        """
        # Generate random but consistent prediction based on image hash
        import hashlib
        with open(image_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()

        # Use hash to generate "prediction"
        hash_int = int(file_hash[:8], 16)
        np.random.seed(hash_int % (2**32))

        # Generate fake probabilities
        probs = np.random.dirichlet(np.ones(len(self.classes)))
        predicted_idx = np.argmax(probs)

        return {
            'predicted_class': self.classes[predicted_idx],
            'confidence': float(probs[predicted_idx]),
            'all_predictions': {
                self.classes[i]: float(probs[i])
                for i in range(len(self.classes))
            },
            'model_type': 'simulated',
            'warning': 'No trained model loaded. Using simulated prediction.'
        }

    def predict_batch(self, image_paths: List[str]) -> List[Dict]:
        """
        Predict for multiple images.

        Args:
            image_paths: List of image paths

        Returns:
            List of prediction results
        """
        return [self.predict(path) for path in image_paths]

    def get_model_summary(self) -> str:
        """Get model architecture summary."""
        if self.model is None:
            return "No model loaded"

        import io
        stream = io.StringIO()
        self.model.summary(print_fn=lambda x: stream.write(x + '\n'))
        return stream.getvalue()

    @staticmethod
    def is_tensorflow_available() -> bool:
        """Check if TensorFlow is available."""
        return TF_AVAILABLE

    @staticmethod
    def is_kagglehub_available() -> bool:
        """Check if kagglehub is available."""
        return KAGGLEHUB_AVAILABLE

    @staticmethod
    def _cleanup_kaggle_partial_archives(dataset_ref: str):
        """Delete partial KaggleHub archives after interrupted downloads."""
        try:
            owner, dataset = dataset_ref.split('/', 1)
        except ValueError:
            return

        cache_root = Path.home() / '.cache' / 'kagglehub' / 'datasets' / owner / dataset
        if not cache_root.exists():
            return

        for pattern in ('*.archive', '*.part', '*.tmp'):
            for partial_file in cache_root.rglob(pattern):
                try:
                    partial_file.unlink()
                except OSError:
                    continue

    def download_kaggle_dataset(self, dataset_ref: str = None, retries: int = 3,
                                retry_wait_seconds: int = 4) -> str:
        """Download a Kaggle dataset and return its local path with retry support."""
        if not KAGGLEHUB_AVAILABLE:
            raise RuntimeError("kagglehub is not installed. Install it with: pip install kagglehub")

        dataset_ref = dataset_ref or self.BRAIN_MRI_DATASET
        last_error = None

        for attempt in range(1, max(1, retries) + 1):
            try:
                path = kagglehub.dataset_download(dataset_ref)
                return str(path)
            except Exception as e:
                last_error = e
                if attempt >= max(1, retries):
                    break

                print(
                    f"Kaggle download failed (attempt {attempt}/{retries}) for {dataset_ref}: {e}. "
                    "Cleaning partial cache and retrying..."
                )
                self._cleanup_kaggle_partial_archives(dataset_ref)
                time.sleep(max(1, retry_wait_seconds))

        raise RuntimeError(
            f"Failed to download dataset '{dataset_ref}' after {max(1, retries)} attempts. "
            f"Last error: {last_error}"
        )

    def train_brain_mri_model(self, epochs: int = 20, batch_size: int = 16,
                              model_type: str = 'mobilenet',
                              save_model_path: str = None,
                              fine_tune: bool = True,
                              download_retries: int = 3) -> Dict:
        """Download Brain MRI dataset from Kaggle and train a model."""
        downloaded_path = self.download_kaggle_dataset(
            self.BRAIN_MRI_DATASET,
            retries=download_retries
        )
        dataset_dir = self.find_dataset_directory(downloaded_path)
        return self.train_from_directory(
            dataset_dir=dataset_dir,
            epochs=epochs,
            batch_size=batch_size,
            model_type=model_type,
            save_model_path=save_model_path,
            fine_tune=fine_tune,
            expected_classes=['no', 'yes']
        )

    def train_chest_xray_model(self, epochs: int = 20, batch_size: int = 16,
                               model_type: str = 'mobilenet',
                               save_model_path: str = None,
                               fine_tune: bool = True,
                               download_retries: int = 3) -> Dict:
        """Download Chest X-ray Pneumonia dataset from Kaggle and train a binary model."""
        downloaded_path = self.download_kaggle_dataset(
            self.CHEST_XRAY_DATASET,
            retries=download_retries
        )
        dataset_dir = self.find_dataset_directory(downloaded_path)
        return self.train_from_directory(
            dataset_dir=dataset_dir,
            epochs=epochs,
            batch_size=batch_size,
            model_type=model_type,
            save_model_path=save_model_path,
            fine_tune=fine_tune,
            expected_classes=['normal', 'pneumonia']
        )

    def train_chest_ctscan_model(self, epochs: int = 20, batch_size: int = 16,
                                 model_type: str = 'mobilenet',
                                 save_model_path: str = None,
                                 fine_tune: bool = True,
                                 download_retries: int = 3) -> Dict:
        """Download Chest CT-Scan dataset from Kaggle and train a multi-class model."""
        downloaded_path = self.download_kaggle_dataset(
            self.CHEST_CTSCAN_DATASET,
            retries=download_retries
        )
        dataset_dir = self.find_dataset_directory(downloaded_path)
        return self.train_from_directory(
            dataset_dir=dataset_dir,
            epochs=epochs,
            batch_size=batch_size,
            model_type=model_type,
            save_model_path=save_model_path,
            fine_tune=fine_tune,
            expected_classes=None
        )

    def train_breast_ultrasound_model(self, epochs: int = 20, batch_size: int = 16,
                                      model_type: str = 'mobilenet',
                                      save_model_path: str = None,
                                      fine_tune: bool = True,
                                      download_retries: int = 3) -> Dict:
        """Download Breast Ultrasound dataset from Kaggle and train a multi-class model."""
        downloaded_path = self.download_kaggle_dataset(
            self.BREAST_ULTRASOUND_DATASET,
            retries=download_retries
        )
        dataset_dir = self.find_dataset_directory(downloaded_path)
        return self.train_from_directory(
            dataset_dir=dataset_dir,
            epochs=epochs,
            batch_size=batch_size,
            model_type=model_type,
            save_model_path=save_model_path,
            fine_tune=fine_tune,
            expected_classes=None
        )

    def train_from_directory(self, dataset_dir: str, epochs: int = 20,
                             batch_size: int = 16, validation_split: float = 0.2,
                             model_type: str = 'mobilenet',
                             save_model_path: str = None,
                             fine_tune: bool = True,
                             expected_classes: List[str] = None) -> Dict:
        """
        Train model from a directory with one subfolder per class.

        Expected structure:
          dataset_dir/
            class_a/
              image1.png
            class_b/
              image2.png
        """
        if not TF_AVAILABLE:
            raise RuntimeError("TensorFlow is required for training")

        dataset_dir = str(dataset_dir)
        if not os.path.isdir(dataset_dir):
            raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")

        train_ds = tf.keras.utils.image_dataset_from_directory(
            dataset_dir,
            validation_split=validation_split,
            subset='training',
            seed=42,
            image_size=(224, 224),
            batch_size=batch_size,
            label_mode='categorical'
        )
        val_ds = tf.keras.utils.image_dataset_from_directory(
            dataset_dir,
            validation_split=validation_split,
            subset='validation',
            seed=42,
            image_size=(224, 224),
            batch_size=batch_size,
            label_mode='categorical'
        )

        self.classes = list(train_ds.class_names)
        num_classes = len(self.classes)

        if expected_classes:
            expected = {c.lower() for c in expected_classes}
            got = {c.lower() for c in self.classes}
            if got != expected:
                raise ValueError(
                    f"Unexpected classes found: {self.classes}. "
                    f"Expected exactly: {sorted(expected)}. "
                    "This usually means dataset root path is wrong."
                )

        # Data augmentation for better generalization on small datasets.
        augmenter = tf.keras.Sequential([
            tf.keras.layers.RandomFlip('horizontal'),
            tf.keras.layers.RandomRotation(0.08),
            tf.keras.layers.RandomZoom(0.12),
            tf.keras.layers.RandomContrast(0.1),
        ])

        train_ds = train_ds.map(lambda x, y: (augmenter(x, training=True), y))

        if model_type == 'simple_cnn':
            self.create_simple_cnn(num_classes=num_classes)
            train_ds = train_ds.map(lambda x, y: (tf.cast(x, tf.float32) / 255.0, y))
            val_ds = val_ds.map(lambda x, y: (tf.cast(x, tf.float32) / 255.0, y))
        else:
            self.create_mobilenet_model(num_classes=num_classes)
            train_ds = train_ds.map(lambda x, y: (mobilenet_preprocess(tf.cast(x, tf.float32)), y))
            val_ds = val_ds.map(lambda x, y: (mobilenet_preprocess(tf.cast(x, tf.float32)), y))

        autotune = tf.data.AUTOTUNE
        train_ds = train_ds.prefetch(autotune)
        val_ds = val_ds.prefetch(autotune)

        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=5,
                restore_best_weights=True
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.3,
                patience=2,
                min_lr=1e-7
            )
        ]

        if model_type == 'mobilenet':
            freeze_epochs = max(1, int(epochs * 0.4))
            finetune_epochs = max(0, epochs - freeze_epochs)

            history_frozen = self.model.fit(
                train_ds,
                validation_data=val_ds,
                epochs=freeze_epochs,
                callbacks=callbacks,
                verbose=1
            )

            history = history_frozen
            if fine_tune and finetune_epochs > 0 and self._base_model is not None:
                self._base_model.trainable = True
                for layer in self._base_model.layers[:-40]:
                    layer.trainable = False

                self.model.compile(
                    optimizer=Adam(learning_rate=1e-5),
                    loss='categorical_crossentropy',
                    metrics=['accuracy']
                )

                history = self.model.fit(
                    train_ds,
                    validation_data=val_ds,
                    initial_epoch=freeze_epochs,
                    epochs=epochs,
                    callbacks=callbacks,
                    verbose=1
                )
        else:
            history = self.model.fit(
                train_ds,
                validation_data=val_ds,
                epochs=epochs,
                callbacks=callbacks,
                verbose=1
            )

        if save_model_path:
            folder = os.path.dirname(save_model_path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            self.save_model(save_model_path)

        final_train_acc = float(history.history.get('accuracy', [0])[-1])
        final_val_acc = float(history.history.get('val_accuracy', [0])[-1])

        return {
            'classes': self.classes,
            'model_type': model_type,
            'epochs': epochs,
            'train_accuracy': final_train_acc,
            'val_accuracy': final_val_acc,
            'dataset_dir': dataset_dir,
            'saved_model': save_model_path or ''
        }

    @classmethod
    def find_dataset_directory(cls, base_path: str) -> str:
        """Find the first directory that looks like class-labeled image dataset."""
        base = Path(base_path)
        if not base.exists():
            raise FileNotFoundError(f"Dataset path not found: {base_path}")

        candidates = []
        if cls._looks_like_class_dataset(base):
            candidates.append(base)

        # Search a few levels down to support Kaggle extraction layouts.
        for path in sorted(base.rglob('*')):
            if path.is_dir() and cls._looks_like_class_dataset(path):
                candidates.append(path)

        if candidates:
            best = max(candidates, key=cls._dataset_score)
            return str(best)

        raise ValueError(
            f"No class-folder image dataset found inside: {base_path}. "
            "Expected at least 2 class folders containing images."
        )

    @classmethod
    def _looks_like_class_dataset(cls, directory: Path) -> bool:
        try:
            class_dirs = [p for p in directory.iterdir() if p.is_dir()]
        except OSError:
            return False
        if len(class_dirs) < 2:
            return False
        valid = 0
        for class_dir in class_dirs:
            try:
                if any(file.suffix.lower() in cls.IMAGE_EXTENSIONS for file in class_dir.iterdir() if file.is_file()):
                    valid += 1
            except OSError:
                continue
        return valid >= 2

    @classmethod
    def _dataset_score(cls, directory: Path) -> int:
        """Score candidate dataset roots; prefer exact binary no/yes folder layouts."""
        try:
            class_dirs = [p for p in directory.iterdir() if p.is_dir()]
        except OSError:
            return -10_000

        class_names = [p.name.lower() for p in class_dirs]
        class_set = set(class_names)

        score = 0
        if class_set == {'no', 'yes'}:
            score += 10_000
        elif {'no', 'yes'}.issubset(class_set):
            score += 4_000
            score -= 300 * (len(class_set) - 2)

        # Reward directories with more image files for stability.
        image_count = 0
        for class_dir in class_dirs:
            try:
                image_count += sum(
                    1 for f in class_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in cls.IMAGE_EXTENSIONS
                )
            except OSError:
                continue

        score += min(image_count, 5000)
        # Prefer shallower folders if score ties.
        score -= len(directory.parts)
        return score

    def _metadata_path(self, model_path: str) -> str:
        return f"{model_path}.meta.json"

    def _save_model_metadata(self, model_path: str):
        metadata = {
            'classes': self.classes,
            'preprocessing_mode': self.preprocessing_mode,
        }
        meta_path = self._metadata_path(model_path)
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

    def _load_model_metadata(self, model_path: str) -> Dict:
        meta_path = self._metadata_path(model_path)
        if not os.path.exists(meta_path):
            return {}
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
