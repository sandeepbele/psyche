import os
import torch
from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding
import numpy as np
from pyannote.audio import Pipeline
from pyannote.audio import Audio
from pyannote.core import Segment
import argparse
import pickle
from scipy.spatial.distance import cdist
import torch.nn.functional as F

@staticmethod
def speaker_db():
    return {
        "Sarah": pickle.load(open("/Users/sandeep/Documents/SB_Sources/anm_dintel/phishnet/sales_rep_embd.pkl", "rb")),
        "Customer_A": pickle.load(open("/Users/sandeep/Documents/SB_Sources/anm_dintel/phishnet/cust_embd.pkl", "rb")),
    }


#audio_file = "/Users/sandeep/Documents/SB_Sources/anm_dintel/phishnet/sales_call.wav"
#sales_rep_ts = [(0.88,1.5),(8.54,21.4),(26.3,108.22)] # list of tuples of start and end times of sales rep speaking
#customer_ts = [(2.32,2.84),(22.74,24.76),(108.96,113.76),(232.4,247.2)] # list of tuples of start and end times of customer speaking

from pyannote.core import Segment
from pyannote.audio import Inference
import numpy as np
from speechbrain.inference.classifiers import EncoderClassifier
from pyannote.audio import Model

embedding_model = None
def fetch_pretrained_model():
    global embedding_model
    if embedding_model is None:
        print("loading model....")
        """embedding_model = PretrainedSpeakerEmbedding(
        "speechbrain/spkrec-ecapa-voxceleb",
        use_auth_token=os.environ.get("HUGGINGFACE_TOKEN"))"""
       
        embedding_model = Model.from_pretrained("speechbrain/spkrec-ecapa-voxceleb", use_auth_token=os.environ.get("HUGGINGFACE_TOKEN"))

    return embedding_model

# need to fix some errors in this function
def get_embeddings_from_waveform_2(waveform, sample_rate=16000):
    classifier = EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb")
    embeddings = classifier.encode_batch(waveform)
    #embeddings = classifier.encode_batch(signal)
    #embeddings = F.normalize(embeddings, dim=2)
    #embeddings = embeddings.squeeze().cpu().numpy()
   # Reshape to 2D - combining batch and num_embeddings dimensions
    # embeddings are tendor of shape [1,1,192]
    embeddings_2d = embeddings.view(-1, embeddings.size(-1))

    # Move to CPU and convert to NumPy
    embeddings_np = embeddings_2d.cpu().numpy()
    return embeddings_np
    

# working version
def get_embeddings_from_waveform(waveform, sample_rate=16000):
    #model = PretrainedSpeakerEmbedding(
    #"speechbrain/spkrec-ecapa-voxceleb",
    #                  use_auth_token=os.environ.get("HUGGINGFACE_TOKEN"))
     # Extract embedding for the current segment
    #waveform = waveform.squeeze()
    #model = fetch_pretrained_model()
    #embedding = model(waveform[None])
    embedding = get_embeddings_from_waveform_2(waveform,sample_rate)
    return embedding

def extract_stacked_embeddings(audio_file, list_of_ts) -> np.ndarray:
    
    # extract embeddings for each segment, 
    #  - where segment is audio sample, often different time intervals in same conversation
    #  - each segmet has its embedding
    #  - embeddings are stacked together and returned as a single array

    audio = Audio(sample_rate=16000, mono="downmix")

    model = PretrainedSpeakerEmbedding(
    "speechbrain/spkrec-ecapa-voxceleb",
                      use_auth_token=os.environ.get("HUGGINGFACE_TOKEN"))
    
    embeddings = []

    for ts in list_of_ts:
        start, end = ts
        segment = Segment(start, end)
        # Extract waveform for the current segment
        waveform, sample_rate = audio.crop(audio_file, segment)
        
        # Extract embedding for the current segment
        embedding = model(waveform[None])
        embeddings.append(embedding)

    return np.vstack(embeddings)


def extract_combined_embedding(audio_file, list_of_ts)-> np.ndarray:

    # extract embeddings from combined audio obtained by concatenating all segments, 
    #  - where segment is audio sample, often different time intervals in same conversation
    
    audio = Audio(sample_rate=16000, mono="downmix")
    
    model = PretrainedSpeakerEmbedding(
    "speechbrain/spkrec-ecapa-voxceleb",
                      use_auth_token=os.environ.get("HUGGINGFACE_TOKEN"))
    
    # Initialize an empty list to store waveforms of each segment
    waveform_segments = []

    for ts in list_of_ts:
        start, end = ts
        segment = Segment(start, end)
        # Extract waveform for the current segment
        waveform, sample_rate = audio.crop(audio_file, segment)
        # Ensure waveform is 2D
        if waveform.ndim == 1:
            waveform = waveform.unsqueeze(0)
        
        waveform_segments.append(waveform)
        
    combined_waveform = torch.cat(waveform_segments, dim=1)
    # Extract a single embedding from the combined waveform
    combined_embedding = model(combined_waveform[None])

    return combined_embedding


def vote_by_average(embeddings,threshold) -> bool:
    return np.all(np.mean(embeddings, axis=0) < threshold)

def vote_by_majority(embeddings,threshold) -> bool:
    return np.all(np.sum(embeddings < threshold, axis=0) > len(embeddings) / 2)

def perform_matching(ref_embedding, target_embedding, threshold=0.85, metric="cosine", method="majority") -> bool:
    
    # Compare embeddings using "cosine" distance
    distance = cdist(ref_embedding, target_embedding, metric=metric)

    if method == "average":
        return vote_by_average(distance,threshold)
    elif method == "majority":
        return vote_by_majority(distance,threshold)
    else:
        raise ValueError(f"Unknown method: {method}")
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Speaker Embedding Matching")
    subparsers = parser.add_subparsers(dest="command")

    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract embeddings")
    extract_parser.add_argument("--audio_file", type=str, help="Path to the audio file")
    extract_parser.add_argument("--ts", type=str, help="Time segments in the format [(start1,end1),(start2,end2),...]")
    extract_parser.add_argument("--output_file", type=str, help="Path to the output file for embeddings")

    # Match command
    match_parser = subparsers.add_parser("match", help="Perform matching")
    match_parser.add_argument("--ref_embedding_file", type=str, help="Path to the reference embedding file")
    match_parser.add_argument("--target_embedding_file", type=str, help="Path to the target embedding file")

    args = parser.parse_args()

    if args.command == "extract":
        audio_file = args.audio_file
        time_segments = eval(args.ts)  # Convert string to list of tuples
        output_file = args.output_file

        # Extract embeddings
        embeddings = extract_stacked_embeddings(audio_file, time_segments)

        # Dump embeddings to file
        with open(output_file, "wb") as f:
            pickle.dump(embeddings, f)

    elif args.command == "match":
        ref_embedding_file = args.ref_embedding_file
        target_embedding_file = args.target_embedding_file

        with open(ref_embedding_file, "rb") as f:
            ref_embedding = pickle.load(f)
        with open(target_embedding_file, "rb") as f:
            target_embedding = pickle.load(f)

        # Perform matching
        match = perform_matching(ref_embedding, target_embedding)
        print("Match" if match else "No Match")



"""
sales_rep_embedding = extract_combined_embedding(audio_file,sales_rep_ts)
customer_embedding = extract_combined_embedding(audio_file,customer_ts)

threshold = 0.2  # threshold for cosine distance

# compare embeddings using "cosine" distance
from scipy.spatial.distance import cdist
distance = cdist(sales_rep_embedding, customer_embedding, metric="cosine")

print("match" if distance < threshold else "no match")
distance = cdist(sales_rep_embedding, sales_rep_embedding, metric="cosine")
print("match" if distance < threshold else "no match")
distance = cdist(customer_embedding, customer_embedding, metric="cosine")
print("match" if distance < threshold else "no match")

new_embedding = extract_combined_embedding(audio_file,[(305.76,309.94)])
distance = cdist(sales_rep_embedding, new_embedding, metric="cosine")
print("match" if distance < threshold else "no match")

#########################################
threshold = 0.85
sales_rep_embedding = extract_stacked_embeddings(audio_file,sales_rep_ts)
customer_embedding = extract_stacked_embeddings(audio_file,customer_ts)

    


distance = cdist(sales_rep_embedding, customer_embedding, metric="cosine")
print(vote_by_average(distance,threshold))
print(vote_by_majority(distance,threshold))

print("avg:match" if vote_by_average(distance,threshold) else "avg:no match")
print("maj:match" if vote_by_majority(distance,threshold) else "maj:no match")

distance = cdist(sales_rep_embedding, sales_rep_embedding, metric="cosine")
print("avg:match" if vote_by_average(distance,threshold) else "avg:no match")
print("maj:match" if vote_by_majority(distance,threshold) else "maj:no match")

distance = cdist(customer_embedding, customer_embedding, metric="cosine")
print("avg:match" if vote_by_average(distance,threshold) else "avg:no match")
print("maj:match" if vote_by_majority(distance,threshold) else "maj:no match")

new_embedding = extract_stacked_embeddings(audio_file,[(305.76,309.94)])
distance = cdist(sales_rep_embedding, new_embedding, metric="cosine")
print("avg:match" if vote_by_average(distance,threshold) else "avg:no match")
print("maj:match" if vote_by_majority(distance,threshold) else "maj:no match")

# write command line 1) that dump sales rep and customer embeddings to file or stdout 2) perform matching

                               """