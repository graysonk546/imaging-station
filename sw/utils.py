import cv2
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import PIL
import torch
import torchvision
import torchvision.transforms.functional as F
import torchvision.transforms.transforms as T

class ModelHelper:
    def __init__(self, model_path):
        self.mapping = {
            1: "M2",
            2: "M3",
            #3: "M4",
            #4: "I4",
            #5: "I6",
            #6: "I8",
        }
        self.device = torch.device('cuda') if torch.cuda.is_available() else \
                      torch.device('cpu')
        self.model = torch.jit.load(model_path, map_location=self.device)
        self.model.eval()

    def convert_to_tensor(self, image_path):
        tensor = PIL.Image.open(image_path).convert("RGB")
        tensor = F.pil_to_tensor(tensor)
        tensor = F.convert_image_dtype(tensor)
        tensor.to(self.device)

        return tensor

    def batch(self, tensors):
        return (torch.stack(tensors), ({}))

    def unbatch(self, batch):
      """
      Unbatches a batch of data from the DataLoader.
      Inputs
        batch: tuple
          Tuple containing a batch from the Dataloader.
      Returns
        X: list
          List of images.
        y: list
          List of dictionaries.
      """
      X, y = batch
      X = [x.to(self.device) for x in X]
      y = [{k: v.to(self.device) for k, v in t.items()} for t in y]
      return X, y

    @torch.no_grad()
    def predict_batch(self, batch):
      """
      Gets the predictions for a batch of data.
      Inputs
        batch: tuple
          Tuple containing a batch from the Dataloder.
        model: torch model
        device: str
            Indicates which device (CPU/GPU) to use.
      Returns
        images: list
          List of tensors of the images.
        predictions: list
          List of dicts containing the predictions for the 
          bounding boxes, labels and confidence scores.
      """
      self.model.to(self.device)
      self.model.eval()
      X, _ = self.unbatch(batch)
      predictions = self.model(X)
      return [x.cpu() for x in X], predictions[1]

    def decode_prediction(self,
                          predictions,
                          score_threshold = 0.7,
                          nms_iou_threshold = 0.2):
      """
      Inputs
        prediction: dict
        score_threshold: float
        nms_iou_threshold: float
      Returns
        prediction: tuple
      """
      res = []
      for prediction in predictions:
          boxes = prediction['boxes']
          scores = prediction['scores']
          labels = prediction['labels']

          if score_threshold:
            want = scores > score_threshold
            boxes = boxes[want]
            scores = scores[want]
            labels = labels[want]

          if nms_iou_threshold:
            want = torchvision.ops.nms(boxes = boxes, 
                                       scores = scores, 
                                       iou_threshold = nms_iou_threshold)
            boxes = boxes[want]
            scores = scores[want]
            labels = labels[want]

          res.append((boxes.cpu().numpy(),
                  labels.cpu().numpy(),
                  scores.cpu().numpy()))
      return res

    def predict_single_image(self, img, score_threshold=0.7):
        transform = T.Compose([
            T.ToTensor()
        ])

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = transform(img)

        batch = (torch.stack([img]), ({}))
        _, predictions = self.predict_batch(batch)

        prediction = self.decode_prediction(predictions, score_threshold=score_threshold)[0]

        return prediction

class DisplayHelper:
    def draw_prediction(self, img, prediction):
        boxes, labels, scores = prediction
        for i, b in enumerate(boxes):
            b_ints = []
            for val in b:
                b_ints.append(val.astype(int))

            img = cv2.rectangle(img, (b_ints[0], b_ints[1]), (b_ints[2], b_ints[3]), (36, 255, 12), 3)
            img = cv2.putText(img, "{}: {:.3f}".format(self.mapping[labels[i]], scores[i]), (b_ints[0], b_ints[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (36, 255, 12), 5)

        return img

    def crop_scale(self, img, scale = 0.6):
        width, height = img.shape[1], img.shape[0]
        crop_width = int(width * scale / 2)
        crop_height = int(height * scale / 2)

        mid_x, mid_y = int(width/2), int(height/2)
        cropped = img[mid_y-crop_height:mid_y+crop_height, mid_x-crop_width:mid_x+crop_width]
        scaled = cv2.resize(cropped, (int(cropped.shape[1]/scale), int(cropped.shape[0]/scale)))
        return scaled
                                      
    def draw_prediction(self, img, prediction, mapping):
        boxes, labels, scores = prediction
        for i, b in enumerate(boxes):
            b_ints = []
            for val in b:
                b_ints.append(val.astype(int))

            img = cv2.rectangle(img, (b_ints[0], b_ints[1]), (b_ints[2], b_ints[3]), (36, 255, 12), 3)
            img = cv2.putText(img, "{}: {:.3f}".format(mapping[labels[i]], scores[i]), (b_ints[0], b_ints[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (36, 255, 12), 5)

        return img

    def crop_scale(self, img, scale = 0.6):
        width, height = img.shape[1], img.shape[0]
        crop_width = int(width * scale / 2)
        crop_height = int(height * scale / 2)

        mid_x, mid_y = int(width/2), int(height/2)
        cropped = img[mid_y-crop_height:mid_y+crop_height, mid_x-crop_width:mid_x+crop_width]
        scaled = cv2.resize(cropped, (int(cropped.shape[1]/scale), int(cropped.shape[0]/scale)))
        return scaled

    def display_single(self, image, prediction):
        boxes, labels, scores = prediction
        fig, ax = plt.subplots(figsize = [15, 15])
        ax.imshow(image.permute(1, 2, 0).numpy())
        for i, b in enumerate(boxes):
            rect = patches.Rectangle(b[:2].astype(int),
                                     (b[2] - b[0]).astype(int),
                                     (b[3] - b[1]).astype(int),
                                     linewidth = 1,
                                     edgecolor = "r",
                                     facecolor = "none")
        ax.add_patch(rect)
        ax.text(b[0].astype(int),
                b[1].astype(int) - 5,
                "{} : {:.3f}".format('fastener', scores[i]), 
                color = "r")
        plt.show()
