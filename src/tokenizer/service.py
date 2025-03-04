import spacy
import logging
import re
from enum import Enum
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

nlp = spacy.load("pt_core_news_sm")
nlp.add_pipe("sentencizer")

class SplitType(Enum):
    COMMA = 'COMMA'
    PUNCTUATION = 'PUNCTUATION'
    EXCLAMATION = 'EXCLAMATION'
    QUESTION = 'QUESTION'
    WORD = 'WORD'


def currency_parser(text):
    """Substitui valores monetários por 'R$'."""
    currency_symbols = ['R$', 'US$', '€', '£', '¥', '₹', '₽', '₿', '฿', '₺', '₴', '₸', '₡', '₮', '₩', '₦', '₲', '₵', '₶', '₷', '₸', '₹', '₺', '₻', '₼', '₽', '₾', '₿']
    currency_symbols = '|'.join(currency_symbols)
    text = re.sub(rf'({currency_symbols})\s?(\d+)', 'R$ \\2', text)
    return text


class Tokenizer:
    def split_sentence_portuguese(self, text, min_length=0, max_length=100):
        """Divide texto em sentenças respeitando tamanho mínimo e máximo e fluidez."""
        logger.info(f"Processando texto: {text}")
        
        if len(text) < max_length:
            logger.warning(f"Texto muito curto ({len(text)} caracteres)")
            return [text]
        
        text_splits = []
        doc = nlp(text)
        
        for sent in doc.sents:
            sentence = str(sent).strip()
            if len(sentence) <= max_length:
                text_splits.append(sentence)
            else:
                splits = self.intelligent_sentence_split(sentence, min_length, max_length)
                text_splits.extend(splits)
                logger.info(f"Divisão inteligente: {splits}")

        final_splits = self.concat_sentences_with_variation(text_splits, max_length)
        logger.info(f"Resultado final: {final_splits}")
        
        return final_splits

    def is_grammatically_correct(self, sentence):
        """Verifica se a sentença é gramaticalmente correta usando o SpaCy."""
        doc = nlp(sentence)
        result = len(doc) > 1 and all(token.dep_ != 'punct' for token in doc)
        logger.info(f"Sentença '{sentence}' é gramaticalmente correta: {result}")
        return result

    def intelligent_sentence_split(self, sentence, min_length, max_length):
        """Divisão inteligente considerando pausas naturais e terminando com vírgula."""
        logger.info(f"Iniciando divisão inteligente para: '{sentence}'")
        
        doc = nlp(sentence)
        current_part = ""
        text_splits = []

        continuation_words = {'e', 'mas', 'ou', 'pois', 'então', 'porque', 'como', 'também', 'contudo', 'porém', 'todavia', 'logo', 'assim', 'portanto', 'consequentemente', 'além disso', 'dessa forma', 'desta forma', 'dessa maneira', 'desta maneira', 'por conseguinte', 'em suma', 'em resumo', 'por fim', 'enfim', 'finalmente', 'em conclusão', 'para concluir', 'para resumir', 'em síntese', 'em síntese', 'em outras palavras', 'ou seja'}

        for token in doc:
            word = token.text

            if len(current_part) + len(word) + 1 <= max_length:
                current_part = f"{current_part} {word}".strip() if current_part else word
            else:
                if current_part and token.text in continuation_words:
                    text_splits.append(current_part.strip() + ',')
                    current_part = word  
                    logger.info(f"Adicionando parte com continuidade: '{current_part.strip() + ','}'")
                else:
                    last_split_point = current_part.rfind(',')
                    if last_split_point == -1:  
                        last_split_point = current_part.rfind(' ')

                    if last_split_point == -1:
                        last_split_point = max_length

                    text_splits.append(current_part[:last_split_point].strip() + ',')
                    logger.info(f"Dividindo antes da palavra atual: '{current_part[:last_split_point].strip() + ','}'")
                    current_part = current_part[last_split_point:].strip() + ' ' + word

            if token.text in {'.', '?', '!'}:
                if current_part:
                    text_splits.append(current_part.strip() + ',')
                    logger.info(f"Adicionando parte final por pontuação: '{current_part.strip() + ','}'")
                current_part = ""

        if current_part:
            text_splits.append(current_part.strip() + ',')
            logger.info(f"Parte remanescente adicionada: '{current_part.strip() + ','}'")

        text_splits = self.split_long_sentences(text_splits, max_length)

        return text_splits

    def split_long_sentences(self, sentences, max_length):
        """Divide sentenças que excedem o limite máximo, sem usar loops repetitivos."""
        final_splits = []
        
        for sentence in sentences:
            logger.info(f"Processando sentença: '{sentence}' (Comprimento: {len(sentence)} / Máximo permitido: {max_length})")

            if len(sentence) > max_length:
                logger.info(f"Sentença excede o limite de {max_length} caracteres, procurando ponto de divisão...")

                split_point = sentence.rfind(',', 0, max_length)
                if split_point == -1:
                    split_point = sentence.rfind(' ', 0, max_length)

                if split_point != -1:
                    logger.info(f"Dividindo sentença no ponto: {split_point} ('{sentence[split_point]}')")
                    logger.info(f"Parte antes da divisão: '{sentence[:split_point].strip()}'")
                    logger.info(f"Parte restante após divisão: '{sentence[split_point+1:].strip()}'")
                    
                    final_splits.append(sentence[:split_point].strip() + ',')
                    sentence = sentence[split_point+1:].strip()
                else:
                    logger.warning(f"Não foi encontrado ponto de divisão adequado na sentença: '{sentence}'")
            
            final_splits.append(sentence.strip())
            logger.info(f"Sentença final adicionada: '{sentence.strip()}'")
        
        logger.info(f"Processamento de sentenças concluído. Total de partes geradas: {len(final_splits)}")
        return final_splits



    def concat_sentences_with_variation(self, text_splits, max_length):
        """Realiza concatenação final, mantendo a variação e fluidez nas sentenças."""
        final_splits = []
        current_part = ""

        while text_splits:
            split = text_splits.pop(0)
            logger.debug(f"Concatenando sentença: '{split}'")

            if len(current_part) + len(split) + 1 <= max_length:
                current_part = f"{current_part} {split}".strip() if current_part else split
            else:
                if current_part:
                    final_splits.append(current_part.strip())
                    logger.info(f"Adicionando parte final: '{current_part.strip()}'")
                current_part = split

        if current_part:
            final_splits.append(current_part.strip())
            logger.info(f"Adicionando última parte: '{current_part.strip()}'")

        return final_splits

    def pre_process(self, text) -> str:
        """Aplica parsers ao texto."""
        text = currency_parser(text)
        text = self.treatment(text)
        text = self.normalize(text)
        if text[-1] == '.':
            text = text[:-1] + ','
        logger.info(f"Texto pré-processado: '{text}'")
        return text
    
    def treatment(self, text):
        text = text.replace('. ', ' . ').replace('?', ' ? ').replace('!', ' ! ').replace(':', ' : ')
        text = " ".join(text.split()).strip()
        return text
    
    def determine_split_type(self, sentence):
        """Determina o tipo de separação da sentença (exemplo: vírgula ou pontuação final)."""
        split_type = SplitType.COMMA if sentence[-1] == ',' else SplitType.PUNCTUATION
        logger.info(f"Tipo de separação determinado para '{sentence}': {split_type}")
        return split_type
    
    def normalize(self, text):
        new_text = text.replace(' . ', '. ').replace(' ? ', '? ').replace(' ! ', '! ').replace(' , ', ', ').replace(' : ', ': ')
        return new_text.strip()

    def show_sentences(self, sentences):
        for sentence in sentences:
            print(sentence)

    def split_sentences_by_punctuation(self, text):
        """Divide texto em sentenças por pontuação."""
        
        sentences =  re.split(r'(?<=[.!?]) +', text)
        
        self.show_sentences(sentences)
        return sentences