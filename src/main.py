#!/usr/bin/env python3

import typing
import json
import threading
import random
import praw


mutex = threading.Lock()


def main():
    config: list[dict[str, typing.Union[str, list[str]]]] \
        = json.load(open('config.json'))

    for bot in config:
        Bot(
            bot['username'],
            bot['subreddit_names'],
            bot['trigger_words'],
            bot['responses']
        )


class Bot:
    def __init__(self, username: str, subreddit_names: list[str], trigger_words: list[str], responses: list[str]):
        self.username = username
        self.trigger_words = trigger_words
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
            with mutex:
                print(f'\n{self.username}')
                print(f'https://www.reddit.com{submission.permalink}')

                if not (self.trigger(submission.title) or self.trigger(submission.selftext)):
                    print('Non-triggering submission')
                elif submission.author == reddit.user.me():
                    print('My own submission')
                elif already_replied(submission, reddit):
                    print('Already replied to submission')
                else:
                    print('Triggering submission')
                    self.reply_to(submission)

    def stream_comments(self, subreddit_name: str):
        reddit = praw.Reddit(self.username)

        with mutex:
            print(f'\n{self.username}')
            print(f'Streaming comments from r/{subreddit_name}')

        for comment in reddit.subreddit(subreddit_name).stream.comments():
            with mutex:
                print(f'\n{self.username}')
                print(f'https://www.reddit.com{comment.permalink}')

                if not self.trigger(comment.body):
                    print('Non-triggering comment')
                elif comment.author == reddit.user.me():
                    print('My own comment')
                elif already_replied(comment, reddit):
                    print('Already replied to comment')
                else:
                    print('Triggering comment')
                    self.reply_to(comment)

    def trigger(self, input: str):
        for trigger_word in self.trigger_words:
            if trigger_word.casefold() in input.casefold():
                return True

        return False

    def reply_to(self, item: typing.Union[praw.models.Submission, praw.models.Comment]):
        try:
            item.reply(random.choice(self.responses))
        except praw.exceptions.APIException as e:
            print(f'APIException: {e}')


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
