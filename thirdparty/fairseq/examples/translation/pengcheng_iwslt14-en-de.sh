# 下载数据参见prepare-iwslt14.sh

TEXT="/userhome/yuxian/data/nmt/iwslt/iwslt14.tokenized.de-en"
MODEL_DIR="/userhome/yuxian/train_logs/nmt/iwslt14/"

# Preprocess
fairseq-preprocess --source-lang en --target-lang de \
    --trainpref $TEXT/train --validpref $TEXT/valid --testpref $TEXT/test \
    --destdir $TEXT/en-de-bin \
    --workers 20

# Train
CUDA_VISIBLE_DEVICES=1 fairseq-train \
    $TEXT/en-de-bin --save-dir $MODEL_DIR \
    --tensorboard-logdir "tensorboard-log" \
    --arch transformer_iwslt_de_en --share-decoder-input-output-embed \
    --optimizer adam --adam-betas '(0.9, 0.98)' --clip-norm 0.0 \
    --lr 5e-4 --lr-scheduler inverse_sqrt --warmup-updates 4000 \
    --dropout 0.3 --weight-decay 0.0001 \
    --criterion label_smoothed_cross_entropy --label-smoothing 0.1 \
    --max-tokens 4096 \
    --eval-bleu \
    --eval-bleu-args '{"beam": 5, "max_len_a": 1.2, "max_len_b": 10}' \
    --eval-bleu-detok moses \
    --eval-bleu-remove-bpe \
    --eval-bleu-print-samples \
    --best-checkpoint-metric bleu --maximize-best-checkpoint-metric \
    --keep-best-checkpoints 10 --fp16

# Generation
fairseq-generate $TEXT/de-en-bin \
    --gen-subset "test" \
    --path $MODEL_DIR/checkpoint_best.pt \
    --batch-size 128 --beam 1 --remove-bpe \
    --score-reference >iwslt14-de-en.out # only score reference!

# compute ppl
python examples/translation/compute_ppl.py --file iwslt14-de-en.out


# Extract-features
for subset in "test" "valid" "train"; do
  python fairseq_cli/extract_features.py \
  $TEXT/de-en-bin \
  --feature-dir $TEXT/de-en-bin/${subset}-features \
  --gen-subset $subset \
  --path $MODEL_DIR/checkpoint_best.pt \
  --batch-size 128 --beam 1 --remove-bpe \
  --score-reference
done
