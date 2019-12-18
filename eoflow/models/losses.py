import tensorflow as tf
from tensorflow.keras.losses import Loss, Reduction


def cropped_loss(loss_fn):
    """ Wraps loss function. Crops the labels to match the logits size. """

    def _loss_fn(labels, logits):
        logits_shape = tf.shape(logits)
        labels_crop = tf.image.resize_with_crop_or_pad(labels, logits_shape[1], logits_shape[2])

        return loss_fn(labels_crop, logits)

    return _loss_fn


class CategoricalCrossEntropy(Loss):
    """ Wrapper class for cross-entropy with class weights """
    def __init__(self, from_logits=True, class_weights=None, reduction=Reduction.AUTO, name='FocalLoss'):
        """Categorical cross-entropy.

        :param from_logits: Whether predictions are logits or softmax, defaults to True
        :type from_logits: bool
        :param class_weights: Array of class weights to be applied to loss. Needs to be of `n_classes` length
        :type class_weights: np.array
        :param reduction: reduction to be used, defaults to Reduction.AUTO
        :type reduction: tf.keras.losses.Reduction, optional
        :param name: name of the loss, defaults to 'FocalLoss'
        :type name: str
        """
        super().__init__(reduction=reduction, name=name)

        self.from_logits = from_logits
        self.class_weights = class_weights

    def call(self, y_true, y_pred):
        # Perform softmax
        if self.from_logits:
            y_pred = tf.nn.softmax(y_pred)

        # Clip the prediction value to prevent NaN's and Inf's
        epsilon = tf.keras.backend.epsilon()
        y_pred = tf.clip_by_value(y_pred, epsilon, 1.)

        # Calculate Cross Entropy
        loss = -y_true * tf.math.log(y_pred)

        # Multiply cross-entropy with class-wise weights
        if self.class_weights is not None:
            loss = tf.multiply(loss, self.class_weights)

        # Sum over classes
        loss = tf.reduce_sum(loss, axis=-1)

        return loss


class CategoricalFocalLoss(Loss):
    """ Categorical version of focal loss.

    References:
        Official paper: https://arxiv.org/pdf/1708.02002.pdf
        Keras implementation: https://github.com/umbertogriffo/focal-loss-keras
    """

    def __init__(self, gamma=2., alpha=.25, from_logits=True, class_weights=None, reduction=Reduction.AUTO,
                 name='FocalLoss'):
        """Categorical version of focal loss.

        :param gamma: gamma value, defaults to 2.
        :type gamma: float
        :param alpha: alpha value, defaults to .25
        :type alpha: float
        :param from_logits: Whether predictions are logits or softmax, defaults to True
        :type from_logits: bool
        :param class_weights: Array of class weights to be applied to loss. Needs to be of `n_classes` length
        :type class_weights: np.array
        :param reduction: reduction to be used, defaults to Reduction.AUTO
        :type reduction: tf.keras.losses.Reduction, optional
        :param name: name of the loss, defaults to 'FocalLoss'
        :type name: str
        """
        super().__init__(reduction=reduction, name=name)

        self.gamma = gamma
        self.alpha = alpha
        self.from_logits = from_logits
        self.class_weights = class_weights

    def call(self, y_true, y_pred):

        # Perform softmax
        if self.from_logits:
            y_pred = tf.nn.softmax(y_pred)

        # Clip the prediction value to prevent NaN's and Inf's
        epsilon = tf.keras.backend.epsilon()
        y_pred = tf.clip_by_value(y_pred, epsilon, 1.)

        # Calculate Cross Entropy
        cross_entropy = -y_true * tf.math.log(y_pred)

        # Calculate Focal Loss
        loss = self.alpha * tf.math.pow(1 - y_pred, self.gamma) * cross_entropy

        # Multiply focal loss with class-wise weights
        if self.class_weights is not None:
            loss = tf.multiply(cross_entropy, self.class_weights)

        # Sum over classes
        loss = tf.reduce_sum(loss, axis=-1)

        return loss


class JaccardDistanceLoss(Loss):
    """ Implementation of the Jaccard distance, or Intersection over Union IoU loss.

    Jaccard = (|X & Y|)/ (|X|+ |Y| - |X & Y|)
            = sum(|A*B|)/(sum(|A|)+sum(|B|)-sum(|A*B|))

    Implementation taken from https://github.com/keras-team/keras-contrib/blob/master/keras_contrib/losses/jaccard.py
    """
    def __init__(self, smooth=1, from_logits=True, class_weights=None, reduction=Reduction.AUTO, name='JaccardLoss'):
        """ Jaccard distance loss.

        :param smooth: Smoothing factor. Default is 1.
        :type smooth: int
        :param from_logits: Whether predictions are logits or softmax, defaults to True
        :type from_logits: bool
        :param class_weights: Array of class weights to be applied to loss. Needs to be of `n_classes` length
        :type class_weights: np.array
        :param reduction: reduction to be used, defaults to Reduction.AUTO
        :type reduction: tf.keras.losses.Reduction, optional
        :param name: name of the loss, defaults to 'JaccardLoss'
        :type name: str
        """
        super().__init__(reduction=reduction, name=name)

        self.smooth = smooth
        self.from_logits = from_logits

        self.class_weights = class_weights

    def call(self, y_true, y_pred):

        # Perform softmax
        if self.from_logits:
            y_pred = tf.nn.softmax(y_pred)

        intersection = tf.reduce_sum(y_true * y_pred, axis=(1, 2))

        sum_ = tf.reduce_sum(y_true + y_pred, axis=(1, 2))

        jac = (intersection + self.smooth) / (sum_ - intersection + self.smooth)

        loss = (1 - jac) * self.smooth

        if self.class_weights is not None:
            loss = tf.multiply(loss, self.class_weights)

        loss = tf.reduce_sum(loss, axis=-1)

        return loss