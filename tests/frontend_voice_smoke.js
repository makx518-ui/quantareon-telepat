const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const events = [];

class CustomEvent {
  constructor(type, options) {
    this.type = type;
    this.detail = (options && options.detail) || {};
  }
}

function storage() {
  const data = new Map();
  return {
    getItem(key) {
      return data.has(key) ? data.get(key) : null;
    },
    setItem(key, value) {
      data.set(key, String(value));
    }
  };
}

function DummyAudioContext() {}

const windowObject = {
  AudioContext: DummyAudioContext,
  webkitAudioContext: null,
  crypto: { randomUUID: () => 'test-user-id' },
  location: {
    protocol: 'https:',
    host: 'example.test',
    href: 'https://example.test/'
  },
  dispatchEvent(event) {
    events.push(event);
    return true;
  },
  setTimeout,
  clearTimeout
};

const context = {
  window: windowObject,
  document: { documentElement: { lang: 'ru' } },
  localStorage: storage(),
  sessionStorage: storage(),
  crypto: windowObject.crypto,
  CustomEvent,
  console,
  Math,
  Date,
  URL,
  ArrayBuffer,
  Blob,
  Float32Array,
  Int16Array,
  WebSocket: { OPEN: 1 },
  setTimeout,
  clearTimeout
};

vm.createContext(context);
vm.runInContext(
  fs.readFileSync('frontend/telepat-voice.js', 'utf8'),
  context,
  { filename: 'telepat-voice.js' }
);

async function main() {
  const client = context.window.TelepatVoice.create({
    language: 'auto',
    wsUrl: 'wss://example.test/ws/voice'
  });

  client._connectSocket = async () => {};
  client._openMicrophone = async () => {};

  await client.start();

  assert.strictEqual(client.active, true);
  assert.ok(
    events.some(
      (event) =>
        event.type === 'telepat:state' &&
        event.detail.state === 'listening'
    )
  );

  events.length = 0;

  client._onMessage({
    data: JSON.stringify({
      type: 'transcript',
      final: true,
      text: 'first',
      turn_id: 1
    })
  });
  assert.strictEqual(client.currentTurnId, 1);

  client._onMessage({
    data: JSON.stringify({
      type: 'barge_in',
      turn_id: 1
    })
  });
  assert.strictEqual(client.cancelledThroughTurnId, 1);

  client._onMessage({
    data: JSON.stringify({
      type: 'reply',
      text: 'stale',
      turn_id: 1
    })
  });
  assert.strictEqual(
    events.some((event) => event.type === 'telepat:reply'),
    false
  );

  client._onMessage({
    data: JSON.stringify({
      type: 'audio_start',
      turn_id: 1,
      format: 'mp3'
    })
  });
  assert.strictEqual(client.pendingAudioTurnId, 1);

  // The binary frame for cancelled turn 1 is dropped before Audio/Blob use.
  client._onMessage({ data: new ArrayBuffer(8) });
  assert.strictEqual(client.playback, null);

  client._onMessage({
    data: JSON.stringify({
      type: 'transcript',
      final: true,
      text: 'second',
      turn_id: 2
    })
  });
  client._onMessage({
    data: JSON.stringify({
      type: 'reply',
      text: 'current',
      turn_id: 2,
      user_id: 'u',
      session_id: 's',
      avatar_state: 'soft_smile'
    })
  });

  assert.strictEqual(client.currentTurnId, 2);
  assert.ok(
    events.some((event) => event.type === 'telepat:reply')
  );

  events.length = 0;
  client._playMp3 = function (_payload, turnId) {
    this.testPlayedTurnId = turnId;
  };

  client._onMessage({
    data: JSON.stringify({
      type: 'avatar_start',
      turn_id: 2,
      media_type: 'video/mp4',
      engine: 'fake-avatar',
      latency_ms: 12.5
    })
  });
  client._onMessage({ data: new ArrayBuffer(16) });

  assert.ok(client.pendingAvatarMedia);
  assert.strictEqual(client.pendingAvatarMedia.turnId, 2);

  client._onMessage({
    data: JSON.stringify({
      type: 'audio_start',
      turn_id: 2,
      format: 'mp3'
    })
  });
  client._onMessage({ data: new ArrayBuffer(8) });

  const avatarEvent = events.find(
    (event) => event.type === 'telepat:avatar-media'
  );
  assert.ok(avatarEvent);
  assert.strictEqual(avatarEvent.detail.turn_id, 2);
  assert.strictEqual(avatarEvent.detail.media_type, 'video/mp4');
  assert.strictEqual(avatarEvent.detail.engine, 'fake-avatar');
  assert.strictEqual(avatarEvent.detail.muted, true);
  assert.strictEqual(client.pendingAvatarMedia, null);
  assert.strictEqual(client.testPlayedTurnId, 2);

  console.log('TELEPAT frontend voice runtime smoke: ok');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
