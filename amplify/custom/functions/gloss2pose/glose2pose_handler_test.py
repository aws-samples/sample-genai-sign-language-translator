import os

os.environ['POSE_BUCKET'] = "genasl-avatar"
os.environ['ASL_DATA_BUCKET'] = "genasl-data"
os.environ['KEY_PREFIX'] = "aslavatarv2/gloss2pose/lookup/"

os.environ['TABLE_NAME'] = 'Pose_Data6'


if __name__ == "__main__":
    #this doesnot work
    import gloss2pose_handler
    response=gloss2pose_handler.lambda_handler(
        {
            "Gloss": "HI, IX-1P NAME E-M-I-L-Y W-E-B-E-R. IX-1P MACHINE LEARNING SPECIALIST AMAZON WEB SERVICES. TODAY IX-1P-pl TALK ABOUT AMAZON S-A-G-E-M-A-K-E-R. AMAZON S-A-G-E-M-A-K-E-R FULL-MANAGE MACHINE LEARNING SERVICE DEVELOPERS DATA SCIENTISTS CAN USE BUILD TRAIN DEPLOY MACHINE LEARNING MODELS. TODAY, IX-1P-pl TALK ABOUT NOTEBOOK INSTANCES, THIS IX-2P DEEP DIVE. WITH NOTEBOOK INSTANCES S-A-G-E-M-A-K-E-R, ALL START WITH NOTEBOOK, TRUE.",
            "Text": "Hi, my name is Emily Weber. I'm a machine learning specialist at Amazon Web services. And today we're going to talk about Amazon Sage Maker. Amazon Sage Maker is a fully-managed machine learning service that developers and data scientists can use to build train and deploy machine learning models. Today, we're gonna talk about notebook instances and this is your deep dive. So with the notebook instances on stage maker, it all starts with a notebook, right?"
        }
        , {})
    print(response)