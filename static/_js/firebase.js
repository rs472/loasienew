// ==========================================
// 1. FIREBASE IMPORTS & INITIALIZATION
// ==========================================
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";




import { 
  getAuth, 
  createUserWithEmailAndPassword, 
  signInWithEmailAndPassword,
  onAuthStateChanged,
  signOut 
} from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";

import { 
  getFirestore, 
  doc, 
  setDoc, 
  getDoc 
} from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";


const firebaseConfig = {
  apiKey: "AIzaSyBmO8o7TOrBlmDE9TlVRUc3x_mRIOBoIPo",
  authDomain: "loa-it-register.firebaseapp.com",
  databaseURL: "https://loa-it-register-default-rtdb.firebaseio.com",
  projectId: "loa-it-register",
  storageBucket: "loa-it-register.firebasestorage.app",
  messagingSenderId: "589578158423",
  appId: "1:589578158423:web:f961ed8dc9cb6a0da37e12",
  measurementId: "G-42HGBC4Q5K"
};

// TODO: Ensure firebaseConfig is defined or imported prior to running this
// Initialize App and Auth
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
const db = getFirestore(app);

export { createUserWithEmailAndPassword, signInWithEmailAndPassword };

// ==========================================
// 2. AUTHENTICATION STATE OBSERVER (MERGED)
// ==========================================


const userPanel = document.getElementById("user-panel");
const userGreeting = document.getElementById("user-greeting");
const btnLogin = document.getElementById("btnLogin");

onAuthStateChanged(auth, async (user) => {
  if (user) {
    // --- UI Update ---
    const displayName = user.displayName || user.email.split("@")[0];
    if (userGreeting) userGreeting.innerText = `Hello, ${displayName}`;
    if (userPanel) userPanel.style.display = "block";
    if (btnLogin) btnLogin.style.display = "none";

    // --- Cookie Syncing (For Flask Backend) ---
    try {
      const idToken = await user.getIdToken(true); // Force refresh token
      // Set secure cookie accessible across the domain
      document.cookie = `token=${idToken}; path=/; SameSite=Lax; ${window.location.protocol === 'https:' ? 'Secure' : ''}`;
      console.log("Token generated and saved to cookies successfully!");
    } catch (error) {
      console.error("Error retrieving Firebase ID token:", error);
    }

  } else {
    // --- UI Reset ---
    if (userPanel) userPanel.style.display = "none";
    if (btnLogin) btnLogin.style.display = "block";

    // --- Clear Token Cookie ---
    document.cookie = "token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC;";
  }
});

// ==========================================
// 3. LOGIN FUNCTIONALITY
// ==========================================
const loginForm = document.getElementById("loginForm");
if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("eMail").value;
    const password = document.getElementById("passWord").value;

    try {
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      console.log("Logged in as:", userCredential.user.email);
      alert("Welcome Back");
    } catch (error) {
      alert("Couldn't login: " + error.message);
    }
  });
}

// ==========================================
// 4. REGISTRATION & 2FA FUNCTIONALITY
// ==========================================
const registrationForm = document.getElementById("registrationForm");
const verifyForm = document.getElementById("form-verify-code");

// Guarda os dados temporariamente antes da validação do código
let tempRegistrationData = {};

// --- ETAPA 1: Clique no botão "Criar" (#registrationForm) ---
if (registrationForm) {
  registrationForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    // Captura dos valores do formulário
    const username = document.getElementById("userName")?.value.trim() || "";
    const email = document.getElementById("creatEmail")?.value.trim().toLowerCase() || "";
    const company = document.getElementById("userCompany")?.value.trim() || "";
    const password = document.getElementById("newPassword")?.value || "";
    const confirmPass = document.getElementById("confirmPassword")?.value || "";

    // Validações básicas
    if (password !== confirmPass) {
      alert("Error, Password doesn't meet!");
      return;
    }

    if (password.length < 6) {
      alert("Password most have 6 characteres.");
      return;
    }

    // Guarda os dados em memória (NÃO CRIA A CONTA NO FIREBASE AINDA)
    tempRegistrationData = { username, email, company, password };

    const btnCreate = document.getElementById("btnCreate");
    if (btnCreate) {
      btnCreate.disabled = true;
      btnCreate.textContent = "Enviando código...";
    }

    try {
      // Solicita ao backend o envio do código de 6 dígitos por e-mail
      const response = await fetch('/api/send-2fa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // Oculta login/cadastro e exibe apenas a tela do código 2FA
        document.getElementById('loginForm')?.classList.add('hidden');
        document.getElementById('divider')?.classList.add('hidden');
        registrationForm.classList.add('hidden');

        document.getElementById('display-target').textContent = email;
        verifyForm?.classList.remove('hidden');
      } else {
        alert(data.message || "Couldn't get validation key.");
      }
    } catch (error) {
      console.error("Error to request 2FA:", error);
      alert("Error to send code, conection field.");
    } finally {
      if (btnCreate) {
        btnCreate.disabled = false;
        btnCreate.textContent = "Criar";
      }
    }
  });
}


// --- ETAPA 2: Clique no botão "Validar Código" (#btn-verify) ---
if (verifyForm) {
  verifyForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const codeInput = document.getElementById("otp-code")?.value.trim() || "";
    const btnVerify = document.getElementById("btn-verify");

    if (codeInput.length !== 6) {
      alert("Please put a 6 charcteres code.");
      return;
    }

    if (btnVerify) {
      btnVerify.disabled = true;
      btnVerify.textContent = "Verifing...";
    }

    try {
      // 1. Valida o código 2FA com o backend Flask
      const response = await fetch('/api/verify-2fa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: tempRegistrationData.email,
          code: codeInput
        })
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        alert(data.message || "Código incorreto ou expirado.");
        return;
      }

      // 2. CÓDIGO VÁLIDO! Agora sim cria a conta no Firebase Auth
      const userCredential = await createUserWithEmailAndPassword(
        auth,
        tempRegistrationData.email,
        tempRegistrationData.password
      );
      const user = userCredential.user;

      // 3. Salva os dados do perfil no Firestore
      await setDoc(doc(db, "users", user.uid), {
        uid: user.uid,
        username: tempRegistrationData.username,
        email: tempRegistrationData.email,
        company: tempRegistrationData.company,
        created_at: new Date().toISOString()
      });

      alert("Account verified and successfully created!");
      
      // Limpa dados temporários e recarrega
      tempRegistrationData = {};
      registrationForm.reset();
      verifyForm.reset();
      window.location.reload();

    } catch (error) {
      console.error("Error in creation process:", error);
      if (error.code === 'auth/email-already-in-use') {
        alert("This email is already in use by another account.");
      } else {
        alert("Error completing registration: " + error.message);
      }
    } finally {
      if (btnVerify) {
        btnVerify.disabled = false;
        btnVerify.textContent = "Validate Code";
      }
    }
  });
}
// ==========================================
// 5. LOGOUT FUNCTIONALITY
// ==========================================
const btnLogout = document.getElementById("btn-logout");
if (btnLogout) {
  btnLogout.addEventListener("click", () => {
    signOut(auth)
      .then(() => {
        window.location.reload();
      })
      .catch((error) => console.error("Error logging out:", error));
  });
}

// ==========================================
// 6. PROTECTED DOWNLOAD FUNCTION
// ==========================================
export async function downloadFile(filename) {
if (!filename) {
        console.error("No filename provided to downloadFile.");
        return;
    }

  const user = auth.currentUser;

  if (!user) {
    alert("You must be logged in to download this file!");
    return;
  }

  try {
    // 1. Obtiene token actualizado
    const idToken = await user.getIdToken();

    // 2. Hace la petición a Flask con la URL codificada por seguridad
    const response = await fetch(`/api/download/${encodeURIComponent(filename)}`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${idToken}`,
      },
    });

    if (response.status === 401 || response.status === 403) {
      alert("Session expired or unauthorized. Please log in again.");
      return;
    }

    if (!response.ok) {
    const errorText = await response.text();
    console.error("Server Error Response:", errorText);
    throw new Error(`HTTP ${response.status}: Server returned an error page instead of the file.`);
}

    // 3. Convierte el stream en archivo y detona la descarga
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(downloadUrl);

  } catch (error) {
    console.error("Download failed:", error);
    alert("Falha no download: " + error.message);
  }
}
//=============================
//GENERATE KEY BRAINBOT
//=============================
// Variável no escopo do módulo para armazenar o e-mail
let userEmail = null;
// Observa o estado da autenticação ao carregar a página
onAuthStateChanged(auth, (user) => {
    if (user) {
      userEmail = user.email;
      console.log("Authenticated user:", userEmail);
    } else {
      doSomething();
    }
  });

// Função principal de geração da chave
export async function requestKey() {
  if (!userEmail) {
    alert("Waiting for user authentication...");
  }

 try {
  const response = await fetch('/api/register-license', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    // Adicione o campo 'product' aqui:
    body: JSON.stringify({ 
        email: userEmail, 
        product: 'brainbot' // <-- ESSENCIAL
    })
  });

    const data = await response.json();

    if (data.success) {
      alert("Your key has been generated: " + data.license_key);
    } else {
      alert(data.message || "Error generating key.");
    }
  } catch (err) {
    console.error("Error:", err);
    alert("Error connecting to the server.");
  }
}

// Vincula o evento de clique diretamente ao botão pelo ID
document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("btn-request-key");
  if (btn) {
    btn.addEventListener("click", requestKey);
  }
});

// la funcion para "onclik button"
window.downloadFile = downloadFile;


