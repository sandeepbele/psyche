prompt_db = {

            'social_engineering_1': {
                'system_instruction':"""You are cybersecurity expert specialized in detecting social engineering, human manipulation, scam and fraud attempts. \
This is telephonic conversation between 'alledged' support-agent and customer. Customer recieved a random call. He then called back to enquire about the call.\
You are given just part of the conversation at a time. Analyse it along with prior context and deduce if there is any \
social engineering, manipulation or scam attempt going on. Adher to output format.""", 
                
                'input_guidance':"""Conversation below follows the following format: [speaker_id]:text. """, 
                
                'output_guidance':"""Reponse should be in following format i.e. key >>> value where each key and value in on new line. 
Make sure values do not have new lines or if they have they are escaped properly. Key and value should be seperated by >>>. \ 
bolean should be either True or False. summary_transcript should be small, concise and useful for next evaluation. Adher to output format.
social_engineering >>> boolean
scam >>> boolean
reasoning >>> str
conversation_sentiments >>> str
agent_emotions >>> list
customer_emotions >>> list
summary_transcript >>> str // in 80 words or less
""",
            }
        }

def get_prompt_template(prompt_name):
    return prompt_db[prompt_name] or None