#!/usr/bin/env python3

import typing
import json
import threading
import random
import praw
import praw.models
import praw.exceptions


mutex = threading.Lock()


def main():
    config: list[dict[str, typing.Union[str, list[str], float]]] \
        = json.load(open('config.json'))

    for bot in config:
        Bot(
            bot['username'],
            bot['subreddit_names'],
            bot['trigger_words'],
            bot['response_rate'],
            bot['responses']
        )


class Bot:
    def __init__(self, username: str, subreddit_names: list[str], trigger_words: list[str], response_rate: float, responses: list[str]):
        self.username = username
        self.trigger_words = trigger_words
        self.response_rate = response_rate
        self.responses = responses

        for subreddit_name in subreddit_names:
            threading.Thread(
                target=self.stream_submissions,
                args=(subreddit_name,)
            ).start()

            threading.Thread(
                target=self.stream_comments,
                args=(subreddit_name,)
            ).start()

    def stream_submissions(self, subreddit_name: str):
        reddit = praw.Reddit(self.username)

        with mutex:
            print(f'\n{self.username}')
            print(f'Streaming submissions from r/{subreddit_name}')

        for submission in reddit.subreddit(subreddit_name).stream.submissions():
            submission: praw.models.Submission

            with mutex:
                print(f'\n{self.username}')
                print(f'https://www.reddit.com{submission.permalink}')

                triggering = self.has_trigger_word(submission.title) \
                    or self.has_trigger_word(submission.selftext)

                if not triggering:
                    print('Non-triggering submission')
                elif submission.author == reddit.user.me():
                    print('My own submission')
                elif already_replied(submission, reddit):
                    print('Already replied to submission')
                elif self.randomly_skip(False):
                    print('Randomly skipping this submission')
                else:
                    print('Replying to submission')
                    self.reply_to(submission)

    def stream_comments(self, subreddit_name: str):
        reddit = praw.Reddit(self.username)

        with mutex:
            print(f'\n{self.username}')
            print(f'Streaming comments from r/{subreddit_name}')

        for comment in reddit.subreddit(subreddit_name).stream.comments():
            comment: praw.models.Comment

            with mutex:
                print(f'\n{self.username}')
                print(f'https://www.reddit.com{comment.permalink}')

                is_a_reply_to_me = replying_to_me(comment, reddit)
                triggering = self.has_trigger_word(comment.body) \
                    or is_a_reply_to_me

                if not triggering:
                    print('Non-triggering comment')
                elif comment.author == reddit.user.me():
                    print('My own comment')
                elif already_replied(comment, reddit):
                    print('Already replied to comment')
                elif self.randomly_skip(is_a_reply_to_me):
                    print('Randomly skipping this comment')
                else:
                    print('Replying to comment')
                    self.reply_to(comment)

    def has_trigger_word(self, input: str):
        for trigger_word in self.trigger_words:
            if trigger_word.casefold() in input.casefold():
                return True

        return False

    def reply_to(self, item: typing.Union[praw.models.Submission, praw.models.Comment]):
        try:
            item.reply(body=random.choice(self.responses))
        except praw.exceptions.APIException as e:
            print(f'APIException: {e}')

    def randomly_skip(self, is_a_reply_to_me: bool):
        return (not is_a_reply_to_me) and random.random() > self.response_rate


def replying_to_me(comment: praw.models.Comment, reddit: praw.Reddit) -> bool:
    return comment.parent().author == reddit.user.me()


def already_replied(item: typing.Union[praw.models.Submission, praw.models.Comment], reddit: praw.Reddit) -> bool:
    if isinstance(item, praw.models.Submission):
        replies = item.comments
    elif isinstance(item, praw.models.Comment):
        item.refresh()
        replies = item.replies

    replies.replace_more(limit=None)
    for reply in replies:
        if reply.author == reddit.user.me():
            return True

    return False


if __name__ == '__main__':
    main()
