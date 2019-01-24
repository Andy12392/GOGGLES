import os

from joblib import Memory
from PIL import Image
import torch
from torch.utils.data import Dataset
from torchvision import transforms

from goggles.constants import CACHE_DIR
from goggles.data.animals_with_attributes.metadata import load_animals_metadata


class AnimalsDataset(Dataset):
    def __init__(self, root,
                 filter_species_ids=None,
                 required_attributes=None,
                 transform=None,
                 is_training=False,
                 cachedir=None):
        super(AnimalsDataset, self).__init__()

        # mem = Memory(cachedir)
        # metadata_loader = mem.cache()

        self.is_training = is_training
        self._data_dir = root

        required_species, \
        self.attributes, \
        self._image_data = load_animals_metadata(root)

        if filter_species_ids is not None:
            assert type(filter_species_ids) is list
            filter_species_ids = set(filter_species_ids)
            required_species = list(filter(lambda s: s.id in filter_species_ids, required_species))
            self._image_data = list(filter(lambda d: d.species.id in filter_species_ids, self._image_data))
        self._image_data = list(filter(lambda d: d.is_for_training == is_training, self._image_data))
        self._species_labels = {species: label for label, species in enumerate(required_species)}

        if required_attributes is not None:
            assert type(required_attributes) is list
            self.attributes = required_attributes

        elif filter_species_ids is not None:
            attributes = set()
            for species in required_species:
                attributes = attributes.union(species.attributes)
            self.attributes = list(sorted(attributes, key=lambda a: a.id))
        self.num_attributes = len(self.attributes)

        if transform is not None:
            self._transform = transform
        else:
            self._transform = transforms.Compose([transforms.ToTensor()])

    def __len__(self):
        return len(self._image_data)

    def __getitem__(self, idx):
        datum = self._image_data[idx]

        image_file = "" #IMAGE PATH like os.path.join(self._data_dir, 'CUB_200_2011', 'images', datum.path)
        image = Image.open(image_file)
        image = self._transform(image)

        image_label = self._species_labels[datum.species]

        attribute_labels = list()
        for attr in datum.attribute_annotations:
            if attr in self.attributes:
                attribute_labels.append(self.get_attribute_label(attr))
        num_nonzero_attributes = len(attribute_labels)  # 0's will be added for padding
        attribute_labels = sorted(attribute_labels) + ([0] * (self.num_attributes - len(attribute_labels)))

        return image, image_label, attribute_labels, num_nonzero_attributes

    def get_labels(self):
        return {label: species
                for species, label
                in self._species_labels.items()}

    def get_attribute(self, attribute_label):
        return self.attributes[attribute_label - 1]  # attribute labels are 1-indexed

    def get_attribute_label(self, attribute):
        return self.attributes.index(attribute) + 1  # attribute labels are 1-indexed

    @staticmethod
    def custom_collate_fn(batch):
        batch = zip(*batch)  # transpose

        image, label, attributes, \
        num_nonzero_attributes = batch

        image = torch.stack(image)
        label = torch.LongTensor(label)
        attributes = torch.stack([torch.LongTensor(a) for a in attributes])
        padding_idx = torch.LongTensor(num_nonzero_attributes)

        return image, label, attributes, padding_idx

    @staticmethod
    def load_dataset_splits(root_dir, input_image_size, filter_species_ids):
        try:
            transform_resize = transforms.Resize(
                (input_image_size, input_image_size))
        except AttributeError:
            transform_resize = transforms.Scale(
                (input_image_size, input_image_size))

        transform_to_tensor = transforms.ToTensor()
        transform_random_flip = transforms.RandomHorizontalFlip()
        transform_normalize = transforms.Normalize((0.5, 0.5, 0.5),
                                                   (0.5, 0.5, 0.5))

        random_transformation = transforms.Compose([
            transform_random_flip, transform_resize,
            transform_to_tensor, transform_normalize])
        non_random_transformation = transforms.Compose([
            transform_resize, transform_to_tensor, transform_normalize])

        train_dataset_with_random_transformation = AnimalsDataset(
            root_dir, filter_species_ids,
            transform=random_transformation,
            is_training=True)

        train_dataset_with_non_random_transformation = AnimalsDataset(
            root_dir, filter_species_ids,
            transform=non_random_transformation,
            is_training=True)

        test_dataset = AnimalsDataset(
            root_dir, filter_species_ids,
            required_attributes=train_dataset_with_non_random_transformation.attributes,
            transform=non_random_transformation,
            is_training=False)

        return train_dataset_with_random_transformation, train_dataset_with_non_random_transformation, test_dataset



