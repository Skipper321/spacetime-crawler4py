# Decoding
import os
import sys

# General use modules
import string


# sort dictionary by key instead 
# returns a list
def getSortedList(freq:dict):
    valueSorted = sorted(freq, key=freq.get, reverse=True)
    myList = []

    for i in valueSorted:
        current = [i, freq[i]]
        myList.append(current)
    
    return myList

# prints dict
# returns list (optional)
def print(freq:dict) -> list:
    myList = getSortedList(freq)

    for i in myList:
        current = i[0] + " -> " + str(i[1])
        __builtins__.print(current)
    return myList

# retrieves the path
# position = file position path
def getInput(position:int = 1):
    path = sys.argv[position]

    # Check if path exits
    if os.path.exists(path):
        # __builtins__.print("filename : " + path.split("/")[-1])
        return path    
    else:
        __builtins__.print("Path not found! Input: ", path)

# converts char to ascii
def charToAscii(myChar):
    return ord(myChar)

# determines if char is alphanumeric
def isAsciiChar(ch) -> bool:

    aVal = charToAscii(ch)

    # numerical
    if aVal > 47 and aVal < 58:
        return True

    # uppercase
    if aVal > 64 and aVal < 91:
        return True 
    
    # lowercase
    if aVal > 96 and aVal < 123:
        return True 

    return False


# checks if string is valid
# 
# -1 if valid
# index of the first character that is invalid
def isValidWord(word:string):
    # Note: return -1 if valid

    for i in range(0, len(word)):
        if not isAsciiChar(word[i]):        
            return i
    return -1
    
# gets indices of non-alphanumeric characters in a word
def getSliceIndices(word:string):
    indices = []
    for i in range(0, len(word)):
        currentChar = word[i]

        if not isAsciiChar(currentChar):
           indices.append(i)

    return indices

# takes non-alphanumeric word and gets alphanumeric words within that word
def getSlicedWords(bigWord:string, firstSplit = -1):
    splittedWords = []
    prev = 0

    idxs = getSliceIndices(bigWord) # O(N)
    idxs.append(len(bigWord))

    for i in idxs: # O(N) also
        currentWord = bigWord[prev:i]
        if currentWord.isalnum():
            splittedWords.append(bigWord[prev:i])
        prev = i + 1

    return splittedWords

# tokenizer
def tokenize(input_data: str):
    tokens = []

    if os.path.exists(input_data):
        with open(input_data, 'r', encoding='utf8') as f:
            raw_list = f.readlines()
    else:
        raw_list = input_data.splitlines()

    for line in raw_list:
        for word in line.split():

            # note: we don't care if the word is duplicate or not, or sorting
            # we only care about tokens 
            
            # this just checks if word is alphanumeric, and if not, then you can become so

            # valid indices are -1 only
            try:

                valIndex = isValidWord(word)

                if valIndex == -1:
                    tokens.append(word.lower())
                else:
                    wordsSlicedFromWord = getSlicedWords(word)
                    tokens.extend(wordsSlicedFromWord)
            except Exception:
                pass
                # just skip the word entirely if you can't

    return tokens

# gets word frequency
def computeWordFrequencies(tokenList):
    myDict = dict()

    for i in range(0, len(tokenList)):
        currentWord = tokenList[i].casefold()

        if myDict.get(currentWord) == None:
            myDict[currentWord] = 1
        else:
            myDict[currentWord] += 1

    return myDict

if __name__ == '__main__':
    samplePath = getInput()
    tokens = tokenize(samplePath)
    frequencies = computeWordFrequencies(tokens)
    shouldBeSorted = print(frequencies)