from torch import nn
from transformers import AutoConfig, AutoModel

# --- 1. Define the Model Architecture ---
# This class must match the architecture used during training.
# You can copy this class from the original training script.
class SDGClassifier(nn.Module):
    def __init__(self, model_path, pooler_dropout, class_number):
        super().__init__()
        # Architecture only — no pretrained weights. load_state_dict(strict=True)
        # in the caller overwrites every parameter from the fine-tuned checkpoint,
        # so downloading 1.73 GB of luke-large-lite weights here only to discard
        # them was pure cost. Guarded by _assert_checkpoint_covers_model().
        self.bert = AutoModel.from_config(AutoConfig.from_pretrained(model_path))
        
        # Checkpoint stores custom pooler AS bert.pooler (overwrites LUKE's built-in)
        # so assign it directly onto self.bert.pooler, not as self.pooler
        self.bert.pooler = nn.Sequential(
            nn.Linear(self.bert.config.hidden_size, self.bert.config.hidden_size)
        )
        
        self.dropout = nn.Dropout(pooler_dropout)
        self.tanh = nn.Tanh()
        
        # cls.0.* → Sequential
        self.cls = nn.Sequential(
            nn.Linear(self.bert.config.hidden_size, class_number)
        )

    def forward(self, input_ids, attention_mask, token_type_ids, position, labels=None):
        out = self.bert(
            input_ids,
            attention_mask,
            token_type_ids=token_type_ids,
            output_attentions=True,
            output_hidden_states=True,
        )
        hidden = out.last_hidden_state
        mask   = attention_mask.unsqueeze(-1).float()
        avg    = (hidden * mask).sum(1) / mask.sum(1)

        pooled = self.tanh(self.bert.pooler(self.dropout(avg)))
        logits = self.cls(pooled)
        return logits, avg, out.attentions
