import MyMaroclear from './MyMaroclear.jsx'
import MaroclearWidget from './MaroclearWidget.jsx'
import { login, redirectToPrivateApp } from './authApi.js'

export default function LoginPage() {
  return (
    <>
      <MyMaroclear
        onLogin={async ({ username, password, remember }) => {
          await login(username, password, remember);
          redirectToPrivateApp();
        }}
        onBack={() => {
          window.close();
          window.location.href = '/';
        }}
      />
      <MaroclearWidget zIndexOverride={999999} />
    </>
  )
}
