function muteConversation(threadName, duration) {
    let muteUntil = null;
    if (duration) {
        muteUntil = new Date(Date.now() + duration).toISOString();
    } else {
        muteUntil = 'infinite';
    }
    
    let mutedChats = JSON.parse(localStorage.getItem('mutedChats') || '{}');
    mutedChats[threadName] = muteUntil;    
    localStorage.setItem('mutedChats', JSON.stringify(mutedChats));
}

function unmuteConversation(threadName) {
    let mutedChats = JSON.parse(localStorage.getItem('mutedChats') || '{}');
    delete mutedChats[threadName];
    localStorage.setItem('mutedChats', JSON.stringify(mutedChats));
}

function isConversationMuted(threadName) {
    let mutedChats = JSON.parse(localStorage.getItem('mutedChats') || '{}');
    const muteUntil = mutedChats[threadName];

    if (!muteUntil) return false;

    if (muteUntil === 'infinite') return true;
    
    if (new Date() > new Date(muteUntil)) {
        delete mutedChats[threadName];
        localStorage.setItem('mutedChats', JSON.stringify(mutedChats));
        return false;
    }

    return true;
}
